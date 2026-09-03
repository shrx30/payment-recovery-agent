from sqlalchemy.orm import Session

from .models import Payment, ActionLog


def get_payment(db: Session, payment_id: int):
    """
    Read-only tool.
    Fetches a payment without modifying anything.
    """

    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    if payment is None:
        return {
            "success": False,
            "error": "payment_not_found"
        }

    return {
        "success": True,
        "payment": {
            "id": payment.id,
            "user_id": payment.user_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "failure_reason": payment.failure_reason,
            "retry_count": payment.retry_count,
            "dataset_type": payment.dataset_type,
        }
    } 





def verify_payment_status(db: Session, payment_id: int):
    """
    Read-only tool.
    Checks the current status of a payment.
    """

    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    if payment is None:
        return {
            "success": False,
            "error": "payment_not_found"
        }

    return {
        "success": True,
        "payment_id": payment.id,
        "status": payment.status,
        "retry_count": payment.retry_count,
    }


MAX_RETRIES = 3


def retry_payment(
    db: Session,
    payment_id: int,
    idempotency_key: str
):
    """
    Safely retry a failed payment.

    Safety guarantees:
    1. Cannot retry a successful payment.
    2. Cannot exceed MAX_RETRIES.
    3. Same idempotency key cannot execute twice.
    4. Every attempt is written to action_log.
    """

    # Get payment
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    if payment is None:
        return {
            "success": False,
            "error": "payment_not_found"
        }

    # SAFETY 1: Never retry successful payment
    if payment.status == "succeeded":
        return {
            "success": False,
            "error": "already_succeeded"
        }

    # SAFETY 2: Maximum retry limit
    if payment.retry_count >= MAX_RETRIES:
        return {
            "success": False,
            "error": "max_retries_exceeded"
        }

    # SAFETY 3: Idempotency
    existing_log = (
        db.query(ActionLog)
        .filter(
            ActionLog.idempotency_key == idempotency_key
        )
        .first()
    )

    if existing_log:
        return {
            "success": False,
            "error": "duplicate_request",
            "message": "This operation was already processed."
        }

    # Record retry attempt
    payment.retry_count += 1

    # ------------------------------------------------
    # TEMPORARY SIMULATION
    # In the real system this would call the payment
    # gateway instead of directly changing the DB.
    # ------------------------------------------------

    payment.status = "succeeded"

    log = ActionLog(
        payment_id=payment.id,
        tool_name="retry_payment",
        idempotency_key=idempotency_key,
        outcome="succeeded",
    )

    db.add(log)
    db.commit()

    return {
        "success": True,
        "payment_id": payment.id,
        "status": payment.status,
        "retry_count": payment.retry_count,
    }



def notify_user(db, payment_id, message, idempotency_key):
    # Check whether this exact action was already performed
    existing = db.query(ActionLog).filter(
        ActionLog.payment_id == payment_id,
        ActionLog.tool_name == "notify_user",
        ActionLog.idempotency_key == idempotency_key
    ).first()

    if existing:
        return {
            "success": False,
            "error": "already_notified"
        }

    # Verify payment exists
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        return {
            "success": False,
            "error": "payment_not_found"
        }

    # Simulate sending notification
    log = ActionLog(
        payment_id=payment_id,
        tool_name="notify_user",
        idempotency_key=idempotency_key,
        outcome="notification_sent"
    )

    db.add(log)
    db.commit()

    return {
        "success": True,
        "action": "notify_user",
        "message": message
    }



def request_new_payment_method(db, payment_id, message, idempotency_key):
    # Prevent duplicate requests
    existing = db.query(ActionLog).filter(
        ActionLog.payment_id == payment_id,
        ActionLog.tool_name == "request_new_payment_method",
        ActionLog.idempotency_key == idempotency_key
    ).first()

    if existing:
        return {
            "success": False,
            "error": "already_requested"
        }

    # Verify payment exists
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        return {
            "success": False,
            "error": "payment_not_found"
        }

    # Simulate requesting a new payment method
    log = ActionLog(
        payment_id=payment_id,
        tool_name="request_new_payment_method",
        idempotency_key=idempotency_key,
        outcome="new_payment_method_requested"
    )

    db.add(log)
    db.commit()

    return {
        "success": True,
        "action": "request_new_payment_method",
        "message": message
    }



