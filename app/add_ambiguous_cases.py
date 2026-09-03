from app.database import SessionLocal
from app.models import Payment


def add_ambiguous_cases():
    db = SessionLocal()

    cases = [
        {
            "failure_reason": "gateway_response_ambiguous",
            "gateway_message": "Request timed out after authorization step",
            "retry_count": 0,
            "previous_status": "pending",
            "webhook_received": False,
        },
        {
            "failure_reason": "gateway_response_ambiguous",
            "gateway_message": "Connection refused before authorization",
            "retry_count": 0,
            "previous_status": "failed",
            "webhook_received": False,
        },
        {
            "failure_reason": "gateway_response_ambiguous",
            "gateway_message": "Declined - contact issuer",
            "retry_count": 2,
            "previous_status": "failed",
            "webhook_received": True,
        },
        {
            "failure_reason": "gateway_response_ambiguous",
            "gateway_message": "Transaction flagged for review",
            "retry_count": 0,
            "previous_status": "pending",
            "webhook_received": False,
        },
        {
            "failure_reason": "gateway_response_ambiguous",
            "gateway_message": "Request timed out while processing",
            "retry_count": 3,
            "previous_status": "failed",
            "webhook_received": False,
        },
    ]

    for i, case in enumerate(cases, start=1):

        payment = Payment(
            user_id=f"ambiguous_user_{i}",
            amount=1000.0 + i * 100,
            currency="INR",
            status="failed",
            failure_reason=case["failure_reason"],
            retry_count=case["retry_count"],
            dataset_type="ambiguous",
            expected_action=None,
            gateway_message=case["gateway_message"],
            previous_status=case["previous_status"],
            webhook_received=case["webhook_received"],
        )

        db.add(payment)

    db.commit()

    print("Added 5 ambiguous test cases.")

    db.close()


if __name__ == "__main__":
    add_ambiguous_cases()