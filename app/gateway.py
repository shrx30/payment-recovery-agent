import random


def retry_payment(payment):
    """
    Simulate a payment gateway retry deterministically per payment.
    """

    probabilities = {
        "network_error": 0.80,
        "payment_gateway_error": 0.70,
        "bank_timeout": 0.60,
    }

    success_probability = probabilities.get(
        payment.failure_reason,
        0.0
    )

    # Deterministic outcome for each payment.
    # The result does not depend on evaluation order.
    rng = random.Random(42 + payment.id)

    success = rng.random() < success_probability

    return success