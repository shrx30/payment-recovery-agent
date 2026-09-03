import json
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Payment
from .database import Base


# ==========================================
# PATHS
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

JSON_FILE = os.path.join(
    BASE_DIR,
    "payments.json",
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "payment_recovery_eval.db",
)

DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


# ==========================================
# DATABASE
# ==========================================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ==========================================
# LOAD DATASET
# ==========================================

def load_dataset():

    print("=" * 60)
    print("CREATING EVALUATION DATABASE")
    print("=" * 60)

    print(f"JSON file: {JSON_FILE}")
    print(f"Database:  {DATABASE_FILE}")

    # --------------------------------------
    # Check JSON exists
    # --------------------------------------

    if not os.path.exists(JSON_FILE):

        raise FileNotFoundError(
            f"payments.json not found at:\n{JSON_FILE}"
        )

    # --------------------------------------
    # Create tables
    # --------------------------------------

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:

        # ----------------------------------
        # Read JSON
        # ----------------------------------

        with open(
            JSON_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        payments = data["payments"]

        print(
            f"\nRecords found in JSON: {len(payments)}"
        )

        # ----------------------------------
        # Clear old evaluation records
        # ----------------------------------

        deleted = db.query(Payment).delete()

        print(
            f"Existing records removed: {deleted}"
        )

        # ----------------------------------
        # Insert records
        #
        # IMPORTANT:
        # Use enumerate() for database IDs.
        # The generated JSON contains duplicate
        # IDs, so we do NOT use item["id"].
        # ----------------------------------

        for index, item in enumerate(
            payments,
            start=1,
        ):

            payment = Payment(
                id=index,
                user_id=item["user_id"],
                amount=item["amount"],
                currency=item["currency"],
                status=item["status"],
                failure_reason=item["failure_reason"],
                retry_count=item["retry_count"],
                dataset_type="test",
                expected_action=item["expected_action"],
                gateway_message=item["gateway_message"],
                previous_status=item["previous_status"],
                webhook_received=item["webhook_received"],
            )

            db.add(payment)

        # ----------------------------------
        # Commit
        # ----------------------------------

        db.commit()

        print(
            f"Inserted: {len(payments)} payments"
        )

        # ==================================
        # VERIFY DATASET
        # ==================================

        known_reasons = [
            "insufficient_funds",
            "card_declined",
            "network_error",
            "payment_gateway_error",
            "bank_timeout",
        ]

        known = (
            db.query(Payment)
            .filter(
                Payment.failure_reason.in_(
                    known_reasons
                )
            )
            .count()
        )

        ambiguous = (
            db.query(Payment)
            .filter(
                Payment.failure_reason
                == "gateway_response_ambiguous"
            )
            .count()
        )

        total = known + ambiguous

        # ==================================
        # RESULTS
        # ==================================

        print()
        print("=" * 60)
        print("DATABASE CHECK")
        print("=" * 60)

        print(
            f"Known failures:     {known}"
        )

        print(
            f"Ambiguous failures: {ambiguous}"
        )

        print(
            f"Total evaluation:   {total}"
        )

        print("=" * 60)

        # ----------------------------------
        # Verify DB row count
        # ----------------------------------

        db_count = (
            db.query(Payment).count()
        )

        print(
            f"\nDatabase rows:      {db_count}"
        )

        if db_count == len(payments):

            print(
                "STATUS:             PASS"
            )

        else:

            print(
                "STATUS:             FAIL"
            )

        print(
            "\nEvaluation database created successfully."
        )

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    print("STARTING DATASET LOAD...")

    load_dataset()

    print("\nLOAD COMPLETE.")