# ============================================================
# evaluate.py
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Payment
from .agent import decide_action


# ============================================================
# EVALUATION DATABASE
# ============================================================

DATABASE_URL = "sqlite:///./payment_recovery_eval.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================
# EVALUATION
# ============================================================

def evaluate_ambiguous():

    db = SessionLocal()

    try:

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

        # ------------------------------------------
        # LLM metrics
        # ------------------------------------------

        high_confidence = 0
        low_confidence = 0
        audited = 0
        flagged = 0

        decision_llm_calls = 0
        audit_llm_calls = 0

        correct_actions = 0

        # ------------------------------------------
        # Revenue
        # ------------------------------------------

        revenue_recovered = 0.0

        print()
        print("=" * 70)
        print("AMBIGUOUS LLM EVALUATION")
        print("=" * 70)

        print(f"Ambiguous payments found: {total}")

        # ==================================================
        # RUN EACH AMBIGUOUS PAYMENT
        # ==================================================

        for payment in payments:

            print()
            print("-" * 70)
            print(f"Payment: {payment.id}")
            print(f"Failure reason: {payment.failure_reason}")
            print(f"Gateway: {payment.gateway_message}")
            print(f"Retries: {payment.retry_count}")
            print(f"Previous: {payment.previous_status}")
            print(f"Webhook: {payment.webhook_received}")
            print(f"EXPECTED ACTION: {payment.expected_action}")

            # ------------------------------------------
            # LLM decision
            # ------------------------------------------

            try:

                decision = decide_action(payment)

                print(f"LLM DECISION: {decision}")

                actual_action = decision.get("action")
                expected_action = payment.expected_action

                # ======================================
                # FIXED: an "error" action means the LLM
                # call itself failed — count it as an
                # error, not as a wrong/escalated decision,
                # and don't score it against accuracy.
                # ======================================

                if actual_action == "error":

                    errors += 1

                    print(
                        "API ERROR:",
                        decision.get("error"),
                    )

                    continue

                # ======================================
                # ACTION ACCURACY
                # ======================================

                if actual_action == expected_action:
                    correct_actions += 1
                    print("ACTION: CORRECT")
                else:
                    print("ACTION: WRONG")

                # ======================================
                # REASONING METRICS
                # ======================================

                confidence = decision.get("reasoning_confidence")

                if confidence == "high":
                    high_confidence += 1
                elif confidence == "low":
                    low_confidence += 1

                if decision.get("reasoning_audited"):
                    audited += 1
                    audit_llm_calls += 1

                if decision.get("reasoning_flagged"):
                    flagged += 1

                if decision.get("source") == "llm":
                    decision_llm_calls += 1

                # ======================================
                # OUTCOME BUCKET
                # (this script decides only, doesn't execute
                # tools, so "unresolved" here means "would
                # need a follow-up tool call to resolve",
                # not "the system failed")
                # ======================================

                if actual_action == "escalate":
                    escalated += 1
                else:
                    unresolved += 1

            except Exception as e:

                # A genuinely unexpected failure in the eval
                # loop itself (not an LLM API error, which is
                # already caught inside decide_action).
                errors += 1
                print(f"ERROR: {e}")

        # ==================================================
        # METRICS
        # ==================================================

        print()
        print()
        print("=" * 70)
        print("AMBIGUOUS LLM RESULTS")
        print("=" * 70)

        print(f"Test ambiguous payments: {total}")
        print(f"Correct actions:         {correct_actions}")

        # FIXED: wrong actions should exclude errors, which it
        # already did — kept as-is, just clarified.
        print(
            f"Wrong actions:           "
            f"{total - correct_actions - errors}"
        )

        print(f"Escalated:               {escalated}")
        print(f"Unresolved (non-escalate):{unresolved}")
        print(f"Errors:                  {errors}")

        # ------------------------------------------
        # Action accuracy
        # ------------------------------------------

        evaluated = total - errors

        action_accuracy = (
            correct_actions / evaluated * 100
            if evaluated
            else 0
        )

        print(f"Action accuracy:         {action_accuracy:.2f}%")

        # ------------------------------------------
        # Reasoning
        # ------------------------------------------

        print()
        print("--- REASONING METRICS ---")
        print(f"High confidence:         {high_confidence}")
        print(f"Low confidence:          {low_confidence}")
        print(f"Reasoning audited:       {audited}")
        print(f"Reasoning flagged:       {flagged}")

        # ------------------------------------------
        # LLM usage
        # ------------------------------------------

        print()
        print("--- LLM USAGE ---")
        print(f"Decision LLM calls:      {decision_llm_calls}")
        print(f"Audit LLM calls:         {audit_llm_calls}")
        print(
            f"Total LLM calls:         "
            f"{decision_llm_calls + audit_llm_calls}"
        )

        print("=" * 70)

    finally:
        db.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    evaluate_ambiguous()