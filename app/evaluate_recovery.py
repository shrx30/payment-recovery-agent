from .database import SessionLocal
from .models import Payment
from .agent import decide_action, execute_action
import random


def evaluate_recovery():
    random.seed(42)


    db = SessionLocal()

    payments = (
        db.query(Payment)
        .filter(Payment.dataset_type == "test")
        .all()
    )

    total = len(payments)

    recovered = 0
    unresolved = 0
    escalated = 0
    api_errors = 0

    revenue_recovered = 0.0

    for payment in payments:

        try:
            print(
                f"\nPayment {payment.id} | "
                f"{payment.failure_reason} | "
                f"₹{payment.amount}"
            )

            # -----------------------------
            # 1. LLM DECISION
            # -----------------------------
            decision = decide_action(payment)

            print(f"DECISION: {decision}")

            # -----------------------------
            # 2. EXECUTE APPROVED ACTION
            # -----------------------------
            result = execute_action(
                db,
                payment,
                decision
            )

            print(f"RESULT: {result}")

            # -----------------------------
            # 3. CHECK RESULT
            # -----------------------------

            if result.get("status") == "escalated":

                escalated += 1

            elif result.get("success"):

                # Re-read payment from database
                db.refresh(payment)

                if payment.status == "succeeded":

                    recovered += 1
                    revenue_recovered += payment.amount

                else:

                    unresolved += 1

            else:

                unresolved += 1

        except Exception as e:

            api_errors += 1

            print(
                f"ERROR on payment "
                f"{payment.id}: {e}"
            )

    print("\n")
    print("==========================================")
    print("       END-TO-END RECOVERY RESULTS")
    print("==========================================")

    print(f"Payments requested:     {total}")
    print(f"Recovered:              {recovered}")
    print(f"Unresolved:             {unresolved}")
    print(f"Escalated:              {escalated}")
    print(f"Errors:                 {api_errors}")

    successful_attempts = (
        recovered + unresolved + escalated
    )

    recovery_rate = (
        recovered / successful_attempts * 100
        if successful_attempts
        else 0
    )

    print(
        f"Recovery rate:          "
        f"{recovery_rate:.2f}%"
    )

    print(
        f"Revenue recovered:      "
        f"₹{revenue_recovered:.2f}"
    )

    print("==========================================")


if __name__ == "__main__":
    evaluate_recovery()