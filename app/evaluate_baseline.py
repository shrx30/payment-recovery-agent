from .database import SessionLocal
from .models import Payment
from .recovery import decide_recovery


KNOWN_FAILURES = [
    "insufficient_funds",
    "card_declined",
    "network_error",
    "payment_gateway_error",
    "bank_timeout",
]


def evaluate_baseline():

    db = SessionLocal()

    try:
        payments = (
            db.query(Payment)
            .filter(
                Payment.failure_reason.in_(KNOWN_FAILURES)
            )
            .order_by(Payment.id)
            .all()
        )

        recovered = 0
        unresolved = 0
        revenue_recovered = 0.0
        escalated = 0

        print("=" * 60)
        print("DETERMINISTIC BASELINE")
        print("=" * 60)

        for payment in payments:

            decision = decide_recovery(payment)

            action = decision["action"]

            # Use the same synthetic execution semantics
            # as the existing recovery evaluator.
            if action == "retry":
                payment.retry_count += 1

                if payment.expected_action == "retry":
                    payment.status = "succeeded"
                    recovered += 1
                    revenue_recovered += payment.amount
                else:
                    payment.status = "failed"
                    unresolved += 1

            elif action == "notify_user":
                payment.status = "failed"
                unresolved += 1

            elif action == "request_new_payment_method":
                payment.status = "failed"
                unresolved += 1

            elif action == "escalate":
                payment.status = "failed"
                escalated += 1

            elif action == "verify_then_retry":

                payment.retry_count += 1

                if payment.expected_action in (
                    "retry",
                    "verify_then_retry",
                ):
                    payment.status = "succeeded"
                    recovered += 1
                    revenue_recovered += payment.amount
                else:
                    payment.status = "failed"
                    unresolved += 1

            else:
                payment.status = "failed"
                unresolved += 1

        db.commit()

        total = len(payments)

        recovery_rate = (
            recovered / total * 100
            if total
            else 0
        )

        print()
        print("========== BASELINE RESULTS ==========")
        print(f"Test payments:       {total}")
        print(f"Recovered:           {recovered}")
        print(f"Unresolved:          {unresolved}")
        print(f"Recovery rate:       {recovery_rate:.2f}%")
        print(
            f"Revenue recovered:   ₹{revenue_recovered:.2f}"
        )
        print(f"Escalated:           {escalated}")
        print("=======================================")

    finally:
        db.close()


if __name__ == "__main__":
    evaluate_baseline()