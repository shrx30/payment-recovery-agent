from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Payment
from .agent import decide_action


DATABASE_URL = "sqlite:///./payment_recovery_eval.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def analyze_errors():

    db = SessionLocal()

    try:

        payments = (
            db.query(Payment)
            .filter(
                Payment.dataset_type == "test",
                Payment.failure_reason
                == "gateway_response_ambiguous",
            )
            .all()
        )

        confusion = Counter()

        print()
        print("=" * 80)
        print("LLM ERROR ANALYSIS")
        print("=" * 80)

        for payment in payments:

            decision = decide_action(payment)

            llm_action = decision.get(
                "action"
            )

            expected = payment.expected_action

            confusion[
                (expected, llm_action)
            ] += 1

            if llm_action != expected:

                print()
                print("-" * 80)

                print(
                    f"Payment ID: {payment.id}"
                )

                print(
                    f"Gateway: "
                    f"{payment.gateway_message}"
                )

                print(
                    f"Retries: "
                    f"{payment.retry_count}"
                )

                print(
                    f"Previous: "
                    f"{payment.previous_status}"
                )

                print(
                    f"Webhook: "
                    f"{payment.webhook_received}"
                )

                print(
                    f"Expected: "
                    f"{expected}"
                )

                print(
                    f"LLM:      "
                    f"{llm_action}"
                )

                print(
                    f"Reason:   "
                    f"{decision.get('reason')}"
                )

        print()
        print()
        print("=" * 80)
        print("CONFUSION MATRIX")
        print("=" * 80)

        for (
            expected,
            predicted,
        ), count in sorted(
            confusion.items()
        ):

            print(
                f"Expected={expected:<20} "
                f"LLM={predicted:<20} "
                f"Count={count}"
            )

        print("=" * 80)

    finally:

        db.close()


if __name__ == "__main__":

    analyze_errors()