import random

from .database import SessionLocal, Base, engine
from .models import Payment


FAILURE_ACTIONS = {
    "insufficient_funds": "notify_user",
    "card_declined": "request_new_payment_method",
    "network_error": "retry",
    "payment_gateway_error": "retry",
    "bank_timeout": "verify_then_retry",
}


def seed():
    # Fresh dataset
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    random.seed(42)

    failure_reasons = list(FAILURE_ACTIONS.keys())

    payments = []

    # 400 development payments
    for i in range(400):
        reason = random.choice(failure_reasons)

        payments.append(
            Payment(
                user_id=f"U{i + 1:04d}",
                amount=random.choice(
                    [499.0, 999.0, 1499.0, 2499.0, 4999.0, 9999.0]
                ),
                currency="INR",
                status="failed",
                failure_reason=reason,
                retry_count=0,
                dataset_type="development",
                expected_action=FAILURE_ACTIONS[reason],
            )
        )

    # 100 held-out test payments
    for i in range(400, 500):
        reason = random.choice(failure_reasons)

        payments.append(
            Payment(
                user_id=f"U{i + 1:04d}",
                amount=random.choice(
                    [499.0, 999.0, 1499.0, 2499.0, 4999.0, 9999.0]
                ),
                currency="INR",
                status="failed",
                failure_reason=reason,
                retry_count=0,
                dataset_type="test",
                expected_action=FAILURE_ACTIONS[reason],
            )
        )

    db.add_all(payments)
    db.commit()

    print("Created exactly 500 payments.")
    print("Development: 400")
    print("Test: 100")

    db.close()


if __name__ == "__main__":
    seed()