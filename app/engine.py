from .policy import get_policy
from .tools import (
    get_payment,
    verify_payment_status,
    retry_payment,
    notify_user,
    request_new_payment_method,
)


def recover_payment(db, payment_id):

    # 1. Read payment
    result = get_payment(db, payment_id)

    if not result["success"]:
        return {
            "success": False,
            "error": "payment_not_found"
        }

    payment = result["payment"]

    # Already successful
    if payment["status"] == "succeeded":
        return {
            "success": True,
            "status": "already_succeeded"
        }

    failure_reason = payment["failure_reason"]

    # 2. Get policy
    policy = get_policy(failure_reason)

    action = policy["action"]

    # 3. Escalation is a terminal state
    if action == "escalate":
        return {
            "success": False,
            "status": "escalated",
            "reason": failure_reason
        }

    # 4. Execute allowed action
    if action == "notify_user":

        result = notify_user(
            db,
            payment_id,
            "Please add sufficient funds and retry the payment later.",
            f"payment-{payment_id}-notify"
        )

    elif action == "request_new_payment_method":

        result = request_new_payment_method(
            db,
            payment_id,
            "Your payment was declined. Please provide another payment method.",
            f"payment-{payment_id}-new-method"
        )

    elif action == "retry":

        result = retry_payment(
            db,
            payment_id,
            f"payment-{payment_id}-retry-{payment['retry_count'] + 1}"
        )

    elif action == "verify_then_retry":

        verification = verify_payment_status(
            db,
            payment_id
        )

        if not verification["success"]:
            return verification

        result = retry_payment(
            db,
            payment_id,
            f"payment-{payment_id}-retry-{payment['retry_count'] + 1}"
        )

    else:
        return {
            "success": False,
            "status": "escalated",
            "reason": "unknown_action"
        }

    # 5. Verify after action
    final_status = verify_payment_status(
        db,
        payment_id
    )

    return {
        "success": result.get("success", False),
        "action": action,
        "result": result,
        "final_status": final_status
    }