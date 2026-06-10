import os
import uuid
import datetime
import logging
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Job, Transaction, JobSummary
from app.repository.job_repository import JobRepository
from app.utils.data_cleaner import DataCleaner
from app.llm.gemini_client import gemini_client

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "txn_id", "date", "merchant", "amount",
    "currency", "status", "category", "account_id",
}


class JobService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = JobRepository(db)

    def process_job(self, job_id: str, file_path: str):
        job = self.repo.get_job_by_id(job_id)
        if not job:
            logger.error(f"Job {job_id} not found. Aborting.")
            return

        try:
            job.status = "processing"
            self.db.commit()

            # ── Step 1: Read & Validate ────────────────────────────────────────
            df = pd.read_csv(file_path)
            job.row_count_raw = len(df)

            # Normalise column names (strip whitespace)
            df.columns = [c.strip().lower() for c in df.columns]

            # Ensure optional columns exist to prevent KeyError
            if "notes" not in df.columns:
                df["notes"] = ""

            # ── Step 2: Data Cleaning & Anomaly Detection ──────────────────────
            df = DataCleaner.clean_and_process_dataframe(df)
            df = DataCleaner.detect_anomalies(df)
            job.row_count_clean = len(df)
            self.db.commit()

            # ── Step 3: LLM Batch Classification ──────────────────────────────
            uncat_mask = df["category"] == "Uncategorised"
            uncat_df = df[uncat_mask]

            if not uncat_df.empty:
                batch = (
                    uncat_df[["txn_id", "merchant", "amount", "currency", "notes"]]
                    .to_dict(orient="records")
                )
                classified_batch = gemini_client.classify_transactions_batch(batch)
                class_map = {item["txn_id"]: item for item in classified_batch}

                def apply_llm_result(row):
                    if row["txn_id"] in class_map:
                        item = class_map[row["txn_id"]]
                        return pd.Series([
                            item.get("llm_category"),
                            item.get("llm_raw_response"),
                            item.get("llm_failed", False),
                        ])
                    return pd.Series([None, None, False])

                df[["llm_category", "llm_raw_response", "llm_failed"]] = df.apply(
                    apply_llm_result, axis=1
                )
            else:
                df["llm_category"] = None
                df["llm_raw_response"] = None
                df["llm_failed"] = False

            # ── Step 4: Persist Transactions ───────────────────────────────────
            records = df.to_dict(orient="records")
            db_transactions = []
            for r in records:
                t = Transaction(
                    id=str(uuid.uuid4()),
                    job_id=job_id,
                    txn_id=r.get("txn_id"),
                    date=r.get("date"),
                    merchant=r.get("merchant"),
                    amount=r.get("amount"),
                    currency=r.get("currency"),
                    status=r.get("status"),
                    category=r.get("category"),
                    account_id=r.get("account_id"),
                    is_anomaly=bool(r.get("is_anomaly", False)),
                    anomaly_reason=r.get("anomaly_reason"),
                    llm_category=r.get("llm_category"),
                    llm_raw_response=r.get("llm_raw_response"),   # ← now populated
                    llm_failed=bool(r.get("llm_failed", False)),
                )
                db_transactions.append(t)

            self.db.bulk_save_objects(db_transactions)

            # ── Step 5: Compute Summary Stats ─────────────────────────────────
            total_inr = float(df[df["currency"] == "INR"]["amount"].sum(skipna=True))
            total_usd = float(df[df["currency"] == "USD"]["amount"].sum(skipna=True))

            top_merchants_series = (
                df.groupby("merchant")["amount"]
                .sum()
                .sort_values(ascending=False)
                .head(3)
            )
            top_merchants = [
                {"merchant": m, "total": float(v)}
                for m, v in top_merchants_series.items()
            ]

            anomaly_count = int(df["is_anomaly"].sum())

            # Per-category spend breakdown (assignment requirement)
            effective_category = df["llm_category"].where(
                df["llm_category"].notna(), df["category"]
            )
            df["_effective_category"] = effective_category
            category_breakdown = (
                df.groupby("_effective_category")["amount"]
                .sum()
                .dropna()
                .apply(float)
                .to_dict()
            )

            # ── Step 6: LLM Narrative Summary ─────────────────────────────────
            stats = {
                "total_spend_inr": total_inr,
                "total_spend_usd": total_usd,
                "top_merchants": top_merchants,
                "anomaly_count": anomaly_count,
                "category_breakdown": category_breakdown,
            }

            llm_summary = gemini_client.generate_narrative_summary(stats)
            # generate_narrative_summary NEVER raises — it returns llm_failed=True on failure

            summary = JobSummary(
                job_id=job_id,
                total_spend_inr=total_inr,
                total_spend_usd=total_usd,
                top_merchants=top_merchants,
                anomaly_count=anomaly_count,
                category_breakdown=category_breakdown,          # ← now populated
                narrative=llm_summary.get("narrative"),
                risk_level=llm_summary.get("risk_level"),
                llm_failed=llm_summary.get("llm_failed", False), # ← now tracked
            )
            self.db.add(summary)

            job.status = "completed"
            job.completed_at = datetime.datetime.utcnow()
            self.db.commit()
            logger.info(f"Job {job_id} completed successfully.")

        except Exception as e:
            logger.exception(f"Job {job_id} failed with error: {e}")
            self.db.rollback()
            job = self.repo.get_job_by_id(job_id)
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.datetime.utcnow()
                self.db.commit()
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
