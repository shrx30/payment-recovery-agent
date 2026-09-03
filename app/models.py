from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from sqlalchemy import Boolean

from .database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")

    status = Column(String, nullable=False)
    failure_reason = Column(String, nullable=True)

    retry_count = Column(Integer, default=0)

    dataset_type = Column(String, nullable=True)
    expected_action = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    gateway_message = Column(String, nullable=True)
    previous_status = Column(String, nullable=True)
    webhook_received = Column(Boolean, default=False)


class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(Integer, primary_key=True, index=True)

    payment_id = Column(Integer, nullable=False)

    tool_name = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False)

    outcome = Column(String, nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow)