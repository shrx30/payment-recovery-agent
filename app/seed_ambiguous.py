from .database import SessionLocal
from .models import Payment


AMBIGUOUS_CASES = [
    {
        "user_id": "AMB001",
        "amount": 4999.0,
        "currency": "INR",
        "status": "pending",
        "failure_reason": "unknown",
        "retry_count": 0,
        "gateway_message": "Request timed out after authorization step",
        "previous_status": "pending",
        "webhook_received": False,
    },
    {
        "user_id": "AMB002",
        "amount": 999.0,
        "currency": "INR",
        "status": "failed",
        "failure_reason": "unknown",
        "retry_count": 0,
        "gateway_message": "Connection refused before authorization",
        "previous_status": "failed",
        "webhook_received": False,
    },
    {
        "user_id": "AMB003",
        "amount": 2499.0,
        "currency": "INR",
        "status": "failed",
        "failure_reason": "unknown",
        "retry_count": 2,
        "gateway_message": "Declined - contact issuer",
        "previous_status": "failed",
        "webhook_received": True,
    },
    {
        "user_id": "AMB004",
        "amount": 9999.0,
        "currency": "INR",
        "status": "pending",
        "failure_reason": "unknown",
        "retry_count": 0,
        "gateway_message": "Transaction flagged for review",
        "previous_status": "pending",
        "webhook_received": False,
    },
]


def seed_ambiguous():

    db = SessionLocal()

    for case in AMBIGUOUS_CASES:
        payment = Payment(**case)
        db.add(payment)

    db.commit()

    print(f"Created {len(AMBIGUOUS_CASES)} ambiguous cases.")

    db.close()


if __name__ == "__main__":
    seed_ambiguous()