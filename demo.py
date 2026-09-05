# app/demo.py

from app.database import SessionLocal
from app.models import Payment
from app.agent import decide_action, execute_action


DEMO_IDS = [247, 74, 98]


def print_separator():
    print()
    print("=" * 68)
    print()


def run_demo():
    db = SessionLocal()

    try:
        for payment_id in DEMO_IDS:

            payment = (
                db.query(Payment)
                .filter(Payment.id == payment_id)
                .first()
            )

            if payment is None:
                print(f"Payment {payment_id} not found.")
                continue

            print_separator()

            print(
                f"PAYMENT {payment.id} | "
                f"₹{payment.amount:,.0f}"
            )

            print_separator()

            print(f"MESSAGE: {payment.gateway_message}")
            print(f"RETRIES: {payment.retry_count}")
            print(f"PREVIOUS: {payment.status}")
            print(f"WEBHOOK: {payment.webhook_received}")

            # --------------------------------------------------
            # Decision
            # --------------------------------------------------

            decision = decide_action(payment)

            print()
            print(
                f"EXTRACTED SIGNALS: "
                f"{decision.get('signals', [])}"
            )

            print(
                f"EVIDENCE CLASS: "
                f"{decision.get('evidence_class', 'unknown')}"
            )

            allowed = decision.get("allowed_actions")

            if allowed is not None:
                print(f"ALLOWED ACTIONS: {allowed}")

            print()
            print(
                f"DECISION SOURCE: "
                f"{decision.get('source', 'unknown')}"
            )

            print(
                f"ACTION: "
                f"{decision.get('action', 'unknown')}"
            )

            print(
                f"REASON: "
                f"{decision.get('reason', '')}"
            )

            # --------------------------------------------------
            # Execute
            # --------------------------------------------------

            result = execute_action(db, payment, decision)
            print()

            if result.get("success"):
                print(
                    f"RESULT: SUCCESS — "
                    f"₹{payment.amount:,.0f} RECOVERED"
                )
            else:
                status = result.get("status", "unknown")

                if status == "escalated":
                    print("RESULT: ESCALATED")
                else:
                    print(
                        f"RESULT: {status.upper()}"
                    )

            print_separator()

    finally:
        db.close()


if __name__ == "__main__":
    run_demo()