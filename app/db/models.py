from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey,
    Text, Boolean, JSON, Index,
)
from sqlalchemy.orm import relationship
import datetime
from app.db.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    # status: pending | processing | completed | failed
    status = Column(String, default="pending")
    row_count_raw = Column(Integer, nullable=True)
    row_count_clean = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    transactions = relationship("Transaction", back_populates="job", lazy="select")
    summary = relationship("JobSummary", back_populates="job", uselist=False, lazy="select")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    txn_id = Column(String, nullable=True)
    date = Column(String, nullable=True)
    merchant = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    status = Column(String, nullable=True)
    category = Column(String, nullable=True)
    account_id = Column(String, nullable=True)

    is_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(String, nullable=True)

    llm_category = Column(String, nullable=True)
    llm_raw_response = Column(Text, nullable=True)
    llm_failed = Column(Boolean, default=False)

    job = relationship("Job", back_populates="transactions")

    # Indexes for query performance
    __table_args__ = (
        Index("ix_transactions_job_id", "job_id"),
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_txn_id", "txn_id"),
    )


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, unique=True)

    total_spend_inr = Column(Float, default=0.0)
    total_spend_usd = Column(Float, default=0.0)
    top_merchants = Column(JSON, nullable=True)
    anomaly_count = Column(Integer, default=0)
    # Per-category spend breakdown: {"Food": 1200.0, "Travel": 500.0, ...}
    category_breakdown = Column(JSON, nullable=True)
    narrative = Column(Text, nullable=True)
    risk_level = Column(String, nullable=True)
    # True if the LLM narrative call failed after all retries
    llm_failed = Column(Boolean, default=False)

    job = relationship("Job", back_populates="summary")
