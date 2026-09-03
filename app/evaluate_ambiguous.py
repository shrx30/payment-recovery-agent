from .database import SessionLocal
from .models import Payment
from .agent import decide_action, execute_action


def evaluate_ambiguous():

    db = SessionLocal()

    payments = (
        db.query(Payment)
        .filter(
            Payment.dataset_type == "test",
            Payment.failure_reason == "gateway_response_ambiguous",
        )
        .all()
    )

    total = len(payments)

    recovered = 0
    unresolved = 0
    escalated = 0
    errors = 0

    high_confidence = 0
    low_confidence = 0
    audited = 0
    flagged = 0

    llm_calls = 0
    audit_calls = 0

    revenue_recovered = 0.0

    print("=" * 70)
    print("       AMBIGUOUS CASE LLM EVALUATION")
    print("=" * 70)

    for payment in payments:

        try:

            print("\n" + "-" * 70)

            print(
                f"Payment: {payment.id}\n"
                f"Failure: {payment.failure_reason}\n"
                f"Message: {payment.gateway_message}\n"
                f"Retries: {payment.retry_count}\n"
                f"Previous: {payment.previous_status}\n"
                f"Webhook: {payment.webhook_received}"
            )

            # ==========================================
            # 1. LLM DECISION
            # ==========================================

            decision = decide_action(payment)

            print(f"\nDECISION: {decision}")

            # This branch is ambiguous, so normally
            # decide_action should use the LLM.
            if decision.get("source") == "llm":
                llm_calls += 1

            # ==========================================
            # 2. REASONING METRICS
            # ==========================================

            confidence = decision.get(
                "reasoning_confidence"
            )

            if confidence == "high":
                high_confidence += 1

            elif confidence == "low":
                low_confidence += 1

            if decision.get("reasoning_audited"):
                audited += 1
                audit_calls += 1

            if decision.get("reasoning_flagged"):
                flagged += 1

            # ==========================================
            # 3. EXECUTE
            # ==========================================

            result = execute_action(
                db,
                payment,
                decision,
            )

            print(f"RESULT: {result}")

            # ==========================================
            # 4. FINAL OUTCOME
            # ==========================================

            if result.get("status") == "escalated":

                escalated += 1

            elif result.get("success"):

                db.refresh(payment)

                if payment.status == "succeeded":

                    recovered += 1
                    revenue_recovered += payment.amount

                else:

                    unresolved += 1

            else:

                unresolved += 1

        except Exception as e:

            errors += 1

            print(
                f"ERROR on payment {payment.id}: {e}"
            )

    # ==============================================
    # FINAL METRICS
    # ==============================================

    print("\n")
    print("=" * 70)
    print("       AMBIGUOUS LLM RESULTS")
    print("=" * 70)

    print(f"Test ambiguous payments: {total}")
    print(f"Recovered:               {recovered}")
    print(f"Unresolved:              {unresolved}")
    print(f"Escalated:               {escalated}")
    print(f"Errors:                  {errors}")

    recovery_rate = (
        recovered / total * 100
        if total
        else 0
    )

    print(
        f"Recovery rate:           "
        f"{recovery_rate:.2f}%"
    )

    print(
        f"Revenue recovered:       "
        f"₹{revenue_recovered:.2f}"
    )

    print("\n--- REASONING METRICS ---")

    print(
        f"High confidence:         "
        f"{high_confidence}"
    )

    print(
        f"Low confidence:          "
        f"{low_confidence}"
    )

    print(
        f"Reasoning audited:       "
        f"{audited}"
    )

    print(
        f"Reasoning flagged:       "
        f"{flagged}"
    )

    print("\n--- LLM USAGE ---")

    print(
        f"Decision LLM calls:      "
        f"{llm_calls}"
    )

    print(
        f"Audit LLM calls:         "
        f"{audit_calls}"
    )

    print(
        f"Total LLM calls:         "
        f"{llm_calls + audit_calls}"
    )

    print("=" * 70)

    db.close()


if __name__ == "__main__":
    evaluate_ambiguous()