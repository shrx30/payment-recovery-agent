from .agent import extract_signals


TEST_CASES = [
    (
        "Request timed out after authorization step",
        {"timeout", "authorization", "post_auth_timeout"},
    ),
    (
        "Connection refused before authorization",
        {"authorization", "pre_auth_failure", "connection_failure"},
    ),
    (
        "Declined - contact issuer",
        {"issuer_decline"},
    ),
    (
        "Transaction flagged for review",
        {"fraud_signal"},
    ),
    (
        "Request timed out while processing",
        {"timeout"},
    ),
]


def main():

    passed = 0

    print("=" * 70)
    print("SIGNAL EXTRACTION TEST")
    print("=" * 70)

    for message, expected in TEST_CASES:

        actual = extract_signals(message)

        print("\nMESSAGE:")
        print(message)

        print("EXPECTED:")
        print(expected)

        print("ACTUAL:")
        print(actual)

        if actual == expected:
            print("PASS")
            passed += 1
        else:
            print("FAIL")

    print("\n" + "=" * 70)
    print(f"RESULT: {passed}/{len(TEST_CASES)} PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()