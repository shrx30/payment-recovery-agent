
import json
import os
import re
import time

from openai import OpenAI, RateLimitError


NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

if not NVIDIA_API_KEY:
    raise RuntimeError("NVIDIA_API_KEY is not set.")

MODEL = "meta/muse-glimmer-30b"

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
    timeout=120.0,
)

# ============================================================
# LLM METRICS
# ============================================================

DECISION_LLM_CALLS = 0
AUDIT_LLM_CALLS = 0


# ============================================================
# CONSTANTS
# ============================================================

MAX_RETRIES = 3

ACTIONS = {
    "retry",
    "verify_then_retry",
    "notify_user",
    "request_new_payment_method",
    "escalate",
}


# ============================================================
# SIGNAL EXTRACTION
# ============================================================

def extract_signals(gateway_message):

    message = (
        gateway_message or ""
    ).lower()

    signals = set()

    # Authorization
    if (
        "authorization" in message
        or "authorized" in message
    ):
        signals.add("authorization")

    # Timeout
    if (
        "timeout" in message
        or "timed out" in message
        or "time out" in message
    ):
        signals.add("timeout")

    # Post-authorization timeout
    if (
        "after authorization" in message
        and (
            "timeout" in message
            or "timed out" in message
            or "connection lost" in message
        )
    ):
        signals.add("post_auth_timeout")

    # Connection failure
    if (
        "connection refused" in message
        or "connection failed" in message
        or "connection failure" in message
        or "connection lost" in message
        or "unable to connect" in message
    ):
        signals.add("connection_failure")

    # Pre-authorization failure
    if (
        "before authorization" in message
        or "prior to authorization" in message
        or "pre-authorization" in message
        or "pre authorization" in message
    ):
        signals.add("pre_auth_failure")

    # Issuer decline
    if (
        "declined" in message
        or "decline" in message
        or "contact issuer" in message
        or "issuer rejected" in message
    ):
        signals.add("issuer_decline")

    # Fraud / review
    if (
        "fraud" in message
        or "flagged for review" in message
        or "transaction flagged" in message
        or "review required" in message
        or "under review" in message
        or "suspicious transaction" in message
    ):
        signals.add("fraud_signal")

    return signals


# ============================================================
# EVIDENCE CLASSIFICATION
# ============================================================

def classify_evidence(signals):

    # Fraud
    if "fraud_signal" in signals:

        return (
            "fraud_signal",
            ["escalate"],
        )

    # Post authorization timeout
    if "post_auth_timeout" in signals:

        return (
            "post_auth_timeout",
            ["verify_then_retry"],
        )

    # Connection failure before authorization
    if (
        "pre_auth_failure" in signals
        and "connection_failure" in signals
    ):

        return (
            "pre_auth_connection_failure",
            [
                "retry",
                "verify_then_retry",
            ],
        )

    # Issuer decline
    if "issuer_decline" in signals:

        return (
            "issuer_decline",
            [
                "notify_user",
                "request_new_payment_method",
            ],
        )

    # Generic connection failure
    if "connection_failure" in signals:

        return (
            "connection_failure",
            [
                "retry",
                "verify_then_retry",
            ],
        )

    # Generic timeout
    if "timeout" in signals:

        return (
            "timeout",
            [
                "retry",
                "verify_then_retry",
            ],
        )

    # Unknown
    return (
        "unknown",
        [
            "verify_then_retry",
            "notify_user",
            "request_new_payment_method",
            "escalate",
        ],
    )


# ============================================================
# JSON EXTRACTION
# ============================================================

def parse_llm_json(content):

    if not content:

        raise ValueError(
            "NVIDIA returned an empty response."
        )

    content = content.strip()

    # --------------------------------------------------------
    # 1. Direct JSON
    # --------------------------------------------------------

    try:

        result = json.loads(content)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # 2. Remove markdown fences
    # --------------------------------------------------------

    cleaned = re.sub(
        r"```(?:json)?",
        "",
        content,
        flags=re.IGNORECASE,
    )

    cleaned = (
        cleaned
        .replace("```", "")
        .strip()
    )

    try:

        result = json.loads(cleaned)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # 3. Find JSON object embedded in text
    # --------------------------------------------------------

    start = cleaned.find("{")

    if start != -1:

        depth = 0
        in_string = False
        escape = False

        for index in range(
            start,
            len(cleaned),
        ):

            char = cleaned[index]

            if escape:

                escape = False
                continue

            if char == "\\":

                escape = True
                continue

            if char == '"':

                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":

                depth += 1

            elif char == "}":

                depth -= 1

                if depth == 0:

                    candidate = cleaned[
                        start:index + 1
                    ]

                    try:

                        result = json.loads(
                            candidate
                        )

                        if isinstance(
                            result,
                            dict,
                        ):
                            return result

                    except json.JSONDecodeError:
                        pass

                    break

    raise ValueError(
        "NVIDIA response was not valid JSON."
    )


# ============================================================
# EXTRACT CONTENT FROM NVIDIA RESPONSE
# ============================================================

def extract_response_text(message):

    # --------------------------------------------------------
    # Normal response
    # --------------------------------------------------------

    content = getattr(
        message,
        "content",
        None,
    )

    if content:

        return content

    # --------------------------------------------------------
    # Reasoning models may expose reasoning_content
    # --------------------------------------------------------

    reasoning_content = getattr(
        message,
        "reasoning_content",
        None,
    )

    if reasoning_content:

        return reasoning_content

    # --------------------------------------------------------
    # Some SDK/model responses may expose output_text
    # --------------------------------------------------------

    output_text = getattr(
        message,
        "output_text",
        None,
    )

    if output_text:

        return output_text

    return None


# ============================================================
# NVIDIA LLM CALL
# ============================================================

def call_nvidia(
    prompt,
    max_attempts=5,
):

    global DECISION_LLM_CALLS

    for attempt in range(
        max_attempts
    ):

        try:

            DECISION_LLM_CALLS += 1

            response = (
                client.chat.completions.create(

                    model=MODEL,

                    messages=[
                        {
                            "role": "system",
                            "content": """
You are a payment recovery decision engine.

Return ONLY one JSON object.

Do NOT output:
- chain of thought
- thinking
- analysis
- numbered lists
- markdown
- code fences
- text before JSON
- text after JSON

Required format:

{
  "action": "ACTION",
  "reason": "SHORT REASON"
}

The action MUST be one of the allowed actions.

Keep the reason under 20 words.

Use only facts present in the gateway evidence.
Do not invent authorization, timeout, fraud,
issuer decline, or other gateway facts.
""",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],

                    temperature=0.0,

                    # Small response because we only need
                    # action + short reason.
                    max_tokens=2000,

                    stream=False,
                )
            )

            # ------------------------------------------------
            # Debug
            # ------------------------------------------------

            print(
                "NVIDIA RESPONSE OBJECT:"
            )

            print(response)

            if not response.choices:

                raise ValueError(
                    "NVIDIA returned no choices."
                )

            message = (
                response
                .choices[0]
                .message
            )

            print(
                "NVIDIA MESSAGE:"
            )

            print(message)

            content = extract_response_text(
                message
            )

            if not content:

                raise ValueError(
                    "NVIDIA returned neither "
                    "content nor reasoning_content."
                )

            print(
                "RAW NVIDIA RESPONSE:"
            )

            print(
                repr(content)
            )

            return parse_llm_json(
                content
            )

        except RateLimitError:

            wait_time = (
                5 * (attempt + 1)
            )

            print(
                f"NVIDIA rate limit. "
                f"Retry {attempt + 1}/"
                f"{max_attempts} "
                f"in {wait_time}s..."
            )

            if (
                attempt
                == max_attempts - 1
            ):

                raise

            time.sleep(
                wait_time
            )


# ============================================================
# REASONING VALIDATION
# ============================================================

def reasoning_is_suspicious(
    reason,
    gateway_message,
    signals,
):

    reason_lower = (
        reason or ""
    ).lower()

    evidence_lower = (
        gateway_message or ""
    ).lower()

    # --------------------------------------------------------
    # Timeout hallucination
    # --------------------------------------------------------

    if (
        "timeout" in reason_lower
        and "timeout" not in evidence_lower
        and "timed out" not in evidence_lower
    ):

        return (
            True,
            "reason mentions timeout but gateway evidence "
            "does not indicate a timeout",
        )

    # --------------------------------------------------------
    # Authorization hallucination
    # --------------------------------------------------------

    if (
        "authorized" in reason_lower
        and "pre_auth_failure" in signals
        and "post_auth_timeout" not in signals
    ):

        return (
            True,
            "reason implies authorization despite "
            "pre-authorization evidence",
        )

    return (
        False,
        None,
    )


# ============================================================
# ACTION SAFETY
# ============================================================

def check_action_safety(
    action,
    signals,
    payment,
    allowed_actions=None,
):

    if allowed_actions is None:

        (
            _,
            allowed_actions,
        ) = classify_evidence(
            signals
        )

    # --------------------------------------------------------
    # Fraud is always escalated
    # --------------------------------------------------------

    if "fraud_signal" in signals:

        if action != "escalate":

            return {
                "safe": False,
                "action": "escalate",
                "reason": (
                    "Fraud/review signal "
                    "requires human review."
                ),
                "policy_violation": True,
            }

    # --------------------------------------------------------
    # Retry limit
    # --------------------------------------------------------

    retry_count = (
        getattr(
            payment,
            "retry_count",
            0,
        )
        or 0
    )

    if retry_count >= MAX_RETRIES:

        if action != "escalate":

            return {
                "safe": False,
                "action": "escalate",
                "reason": (
                    "Maximum retry count reached."
                ),
                "policy_violation": True,
            }

    # --------------------------------------------------------
    # Allowed action validation
    # --------------------------------------------------------

    if action not in allowed_actions:

        return {
            "safe": False,
            "action": "escalate",
            "reason": (
                "LLM selected an action "
                "outside the allowed evidence policy."
            ),
            "policy_violation": True,
        }

    return {
        "safe": True,
        "action": action,
        "reason": (
            "Action is permitted by "
            "the evidence policy."
        ),
        "policy_violation": False,
    }


# ============================================================
# MAIN DECISION
# ============================================================

def decide_action(payment):

    message = (
        getattr(
            payment,
            "gateway_message",
            "",
        )
        or ""
    )

    retry_count = (
        getattr(
            payment,
            "retry_count",
            0,
        )
        or 0
    )

    previous_status = (
        getattr(
            payment,
            "previous_status",
            None,
        )
        or "unknown"
    )

    webhook_received = bool(
        getattr(
            payment,
            "webhook_received",
            False,
        )
    )

    # --------------------------------------------------------
    # Extract evidence
    # --------------------------------------------------------

    signals = extract_signals(
        message
    )

    (
        evidence_class,
        allowed_actions,
    ) = classify_evidence(
        signals
    )

    print()
    print("=" * 70)

    print(
        f"MESSAGE: {message}"
    )

    print(
        f"RETRIES: {retry_count}"
    )

    print(
        f"PREVIOUS: {previous_status}"
    )

    print(
        f"WEBHOOK: {webhook_received}"
    )

    print(
        f"EXTRACTED SIGNALS: {signals}"
    )

    print(
        f"EVIDENCE CLASS: "
        f"{evidence_class}"
    )

    print(
        f"ALLOWED ACTIONS: "
        f"{allowed_actions}"
    )

    # ========================================================
    # HARD SAFETY RULES
    # ========================================================

    if "fraud_signal" in signals:

        return {
            "action": "escalate",
            "reason": (
                "Fraud/review signal requires "
                "human review."
            ),
            "source": "policy",
            "policy_violation": False,
            "evidence_class": evidence_class,
            "signals": list(signals),
        }

    if retry_count >= MAX_RETRIES:

        return {
            "action": "escalate",
            "reason": (
                "Maximum retry count reached."
            ),
            "source": "policy",
            "policy_violation": False,
            "evidence_class": evidence_class,
            "signals": list(signals),
        }

    # ========================================================
    # LLM PROMPT
    # ========================================================

    prompt = f"""
Decide the safest recovery action for this payment.

Gateway message:
"{message}"

Extracted signals:
{sorted(signals)}

Evidence class:
"{evidence_class}"

Retry count:
{retry_count}

Previous status:
"{previous_status}"

Webhook received:
{webhook_received}

Allowed actions:
{json.dumps(allowed_actions)}

ACTION DEFINITIONS:

retry:
Use when evidence indicates the payment did not reach
authorization and retrying is safe.

verify_then_retry:
Use when authorization may have occurred or the result
is uncertain. Verify before retrying.

notify_user:
Use when the user needs to be informed or take action.

request_new_payment_method:
Use when the current payment method should not be retried
and another payment method is required.

escalate:
Use when human review is required.

EVIDENCE RULES:

- "before authorization" means authorization had not occurred
  at that point.
- "after authorization" means authorization may already have
  occurred.
- Do not claim authorization occurred unless evidence supports it.
- Do not mention timeout unless evidence supports timeout.
- Do not invent fraud.
- Do not invent issuer decline.
- Choose ONLY from the allowed actions.

Return ONLY this JSON structure:

{{
  "action": "one_allowed_action",
  "reason": "short evidence-based reason"
}}
"""

    try:

        llm_result = call_nvidia(
            prompt
        )

        llm_action = (
            llm_result.get(
                "action"
            )
        )

        llm_reason = (
            llm_result.get(
                "reason",
                "",
            )
        )

        print(
            "LLM ACTION:",
            llm_action,
        )

        print(
            "LLM REASON:",
            llm_reason,
        )

        # ----------------------------------------------------
        # Validate action
        # ----------------------------------------------------

        safety = check_action_safety(
            llm_action,
            signals,
            payment,
            allowed_actions,
        )

        if not safety["safe"]:

            print(
                "SAFETY OVERRIDE:"
            )

            print(
                safety
            )

            return {
                "action": safety["action"],
                "llm_action": llm_action,
                "reason": safety["reason"],
                "source": "llm",
                "policy_violation": True,
                "evidence_class": evidence_class,
                "signals": list(signals),
            }

        # ----------------------------------------------------
        # Check reasoning
        # ----------------------------------------------------

        (
            suspicious,
            suspicion_reason,
        ) = reasoning_is_suspicious(
            llm_reason,
            message,
            signals,
        )

        if suspicious:

            print(
                "REASONING SUSPICIOUS:",
                suspicion_reason,
            )

            return {
                "action": llm_action,
                "reason": llm_reason,
                "source": "llm",
                "reasoning_confidence": "low",
                "reasoning_audited": False,
                "reasoning_flagged": True,
                "suspicion_reason": suspicion_reason,
                "evidence_class": evidence_class,
                "signals": list(signals),
            }

        # ----------------------------------------------------
        # Valid LLM decision
        # ----------------------------------------------------

        return {
            "action": llm_action,
            "reason": llm_reason,
            "source": "llm",
            "reasoning_confidence": "high",
            "reasoning_audited": False,
            "reasoning_flagged": False,
            "evidence_class": evidence_class,
            "signals": list(signals),
        }

    except Exception as e:

        print(
            "LLM ERROR TYPE:",
            type(e).__name__,
        )

        print(
            "LLM ERROR DETAIL:",
            str(e),
        )

        return {
            "action": "error",
            "reason": (
                "LLM call failed; "
                "human review required."
            ),
            "source": "llm_error",
            "error_type": type(e).__name__,
            "error": str(e),
            "evidence_class": evidence_class,
            "signals": list(signals),
        }


# ============================================================
# ACTION EXECUTION
# ============================================================

def execute_action(
    db,
    payment,
    decision,
):

    action = decision.get(
        "action"
    )

    # --------------------------------------------------------
    # LLM error
    # --------------------------------------------------------

    if action == "error":

        return {
            "success": False,
            "error": decision.get(
                "error",
                "llm_error",
            ),
        }

    # --------------------------------------------------------
    # Escalate
    # --------------------------------------------------------

    if action == "escalate":

        return {
            "success": False,
            "status": "escalated",
            "reason": decision.get(
                "reason"
            ),
        }

    # --------------------------------------------------------
    # Notify user
    # --------------------------------------------------------

    if action == "notify_user":

        if payment.status == "succeeded":

            return {
                "success": False,
                "error": "already_succeeded",
            }

        return {
            "success": False,
            "error": "already_notified",
        }

    # --------------------------------------------------------
    # New payment method
    # --------------------------------------------------------

    if (
        action
        == "request_new_payment_method"
    ):

        return {
            "success": False,
            "status": "awaiting_payment_method",
        }

    # --------------------------------------------------------
    # Verify then retry
    # --------------------------------------------------
        
    # --------------------------------------------------------
    # Verify then retry
    # --------------------------------------------------------
           # --------------------------------------------------------
    # Verify then retry
    # --------------------------------------------------------

    if action == "verify_then_retry":

        if payment.status == "succeeded":

            return {
                "success": True,
                "status": "succeeded",
            }

        payment.retry_count += 1

        if payment.expected_action in (
            "retry",
            "verify_then_retry",
        ):

            payment.status = "succeeded"

            db.commit()

            return {
                "success": True,
                "status": "succeeded",
            }

        payment.status = "failed"

        db.commit()

        return {
            "success": False,
            "status": "failed",
        }

    # --------------------------------------------------------
    # Retry
    # --------------------------------------------------------

    
      
    # --------------------------------------------------------
    # Retry
    # --------------------------------------------------------

    if action == "retry":

        if payment.status == "succeeded":

            return {
                "success": False,
                "error": "already_succeeded",
            }

        payment.retry_count += 1

        if payment.expected_action == "retry":

            payment.status = "succeeded"

            db.commit()

            return {
                "success": True,
                "status": "succeeded",
            }

        payment.status = "failed"

        db.commit()

        return {
            "success": False,
            "status": "failed",
        }

    # --------------------------------------------------------
    # Unknown action
    # --------------------------------------------------------

    return {
        "success": False,
        "error": (
            f"Unknown action: {action}"
        ),
    }

