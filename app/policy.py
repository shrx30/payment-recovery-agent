POLICY = {
    "insufficient_funds": {
        "action": "notify_user",
        "auto_action": True
    },

    "card_declined": {
        "action": "request_new_payment_method",
        "auto_action": True
    },

    "network_error": {
        "action": "retry",
        "auto_action": True
    },

    "payment_gateway_error": {
        "action": "retry",
        "auto_action": True
    },

    "bank_timeout": {
        "action": "verify_then_retry",
        "auto_action": True
    },

    "fraud_suspected": {
        "action": "escalate",
        "auto_action": False
    },

    "unknown": {
        "action": "escalate",
        "auto_action": False
    }
}


def get_policy(failure_reason):
    return POLICY.get(
        failure_reason,
        POLICY["unknown"]
    )