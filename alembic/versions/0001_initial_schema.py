"""Initial schema: jobs, transactions, job_summaries

Revision ID: 0001
Revises:
Create Date: 2026-06-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── jobs ──────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True, server_default="pending"),
        sa.Column("row_count_raw", sa.Integer(), nullable=True),
        sa.Column("row_count_clean", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_id"), "jobs", ["id"], unique=False)

    # ── transactions ──────────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("txn_id", sa.String(), nullable=True),
        sa.Column("date", sa.String(), nullable=True),
        sa.Column("merchant", sa.String(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("anomaly_reason", sa.String(), nullable=True),
        sa.Column("llm_category", sa.String(), nullable=True),
        sa.Column("llm_raw_response", sa.Text(), nullable=True),
        sa.Column("llm_failed", sa.Boolean(), nullable=True, server_default="false"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_job_id",     "transactions", ["job_id"],     unique=False)
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"], unique=False)
    op.create_index("ix_transactions_txn_id",     "transactions", ["txn_id"],     unique=False)

    # ── job_summaries ─────────────────────────────────────────────────────────
    op.create_table(
        "job_summaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("total_spend_inr", sa.Float(), nullable=True, server_default="0"),
        sa.Column("total_spend_usd", sa.Float(), nullable=True, server_default="0"),
        sa.Column("top_merchants", sa.JSON(), nullable=True),
        sa.Column("anomaly_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("category_breakdown", sa.JSON(), nullable=True),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("llm_failed", sa.Boolean(), nullable=True, server_default="false"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index(op.f("ix_job_summaries_id"), "job_summaries", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_summaries_id"), table_name="job_summaries")
    op.drop_table("job_summaries")

    op.drop_index("ix_transactions_txn_id",     table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_index("ix_transactions_job_id",     table_name="transactions")
    op.drop_table("transactions")

    op.drop_index(op.f("ix_jobs_id"), table_name="jobs")
    op.drop_table("jobs")
