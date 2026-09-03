import random


def split_payments(payments):
    random.seed(42)

    payments = payments.copy()
    random.shuffle(payments)

    development = payments[:400]
    test = payments[400:]

    return development, test