from .database import SessionLocal
from .models import Payment
from .engine import recover_payment


def evaluate():
    db = SessionLocal()

    payments = (
        db.query(Payment)
        .filter(Payment.dataset_type == "test")
        .all()
    )

    total = len(payments)
    recovered = 0
    revenue_recovered = 0.0
    escalated = 0

    print("\n========== DETERMINISTIC BASELINE ==========\n")

    for payment in payments:

        result = recover_payment(db, payment.id)

        # Read final payment state
        updated = (
            db.query(Payment)
            .filter(Payment.id == payment.id)
            .first()
        )

        final_status = updated.status

        if final_status == "succeeded":
            recovered += 1
            revenue_recovered += updated.amount

        if result.get("status") == "escalated":
            escalated += 1

        print(
            f"Payment {payment.id} | "
            f"{payment.failure_reason} | "
            f"Action: {result.get('action', result.get('status'))} | "
            f"Final: {final_status}"
        )

    recovery_rate = (
        recovered / total * 100
        if total
        else 0
    )

    print("\n========== RESULTS ==========")
    print(f"Test payments: {total}")
    print(f"Recovered: {recovered}")
    print(f"Unresolved: {total - recovered}")
    print(f"Recovery rate: {recovery_rate:.2f}%")
    print(f"Revenue recovered: ₹{revenue_recovered:.2f}")
    print(f"Escalated: {escalated}")

    db.close()


if __name__ == "__main__":
    evaluate()