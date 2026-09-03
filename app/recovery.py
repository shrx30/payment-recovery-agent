def decide_recovery(payment):
    reason = payment.failure_reason

    if reason == "insufficient_funds":
        return {
            "action": "notify_user",
            "message": "Insufficient funds. Ask the user to add funds and retry later.",
            "retry": False
        }

    elif reason == "network_error":
        return {
            "action": "retry",
            "message": "Temporary network failure. Retry the payment.",
            "retry": True
        }

    elif reason == "bank_timeout":
        return {
            "action": "verify_then_retry",
            "message": "Bank response timed out. Verify payment status before retrying.",
            "retry": True
        }

    elif reason == "payment_gateway_error":
        return {
            "action": "retry",
            "message": "Temporary gateway error. Retry with backoff.",
            "retry": True
        }

    elif reason == "card_declined":
        return {
            "action": "request_new_payment_method",
            "message": "Card was declined. Ask the user for another payment method.",
            "retry": False
        }

    else:
        return {
            "action": "manual_review",
            "message": "Unknown failure reason. Escalate for review.",
            "retry": False
        }