from .database import SessionLocal
from .models import Payment
from .recovery import decide_recovery
from .gateway import retry_payment


def process_payments():
    db = SessionLocal()

    payments = db.query(Payment).filter(
        Payment.status == "failed"
    ).all()

    recovered = 0
    attempted = 0
    unresolved = 0

    for payment in payments:

        decision = decide_recovery(payment)

        print(
            f"Payment {payment.id} | "
            f"{payment.failure_reason} | "
            f"→ {decision['action']}"
        )

        if decision["action"] == "retry":

            attempted += 1

            success = retry_payment(payment)

            if success:
                payment.status = "recovered"
                recovered += 1

                print("   ✓ RECOVERED")

            else:
                unresolved += 1

                print("   ✗ RETRY FAILED")

        elif decision["action"] == "verify_then_retry":

            attempted += 1

            success = retry_payment(payment)

            if success:
                payment.status = "recovered"
                recovered += 1

                print("   ✓ RECOVERED")

            else:
                unresolved += 1

                print("   ✗ STILL FAILED")

        else:
            unresolved += 1

    db.commit()
    db.close()

    print("\n========== RESULTS ==========")
    print(f"Payments processed: {len(payments)}")
    print(f"Recovery attempts: {attempted}")
    print(f"Recovered: {recovered}")
    print(f"Unresolved: {unresolved}")

    if attempted:
        print(
            f"Attempt recovery rate: "
            f"{recovered / attempted * 100:.2f}%"
        )


if __name__ == "__main__":
    process_payments()