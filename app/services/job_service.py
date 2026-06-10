import os
import uuid
import datetime
import pandas as pd
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Job, Transaction, JobSummary
from app.repository.job_repository import JobRepository
from app.utils.data_cleaner import DataCleaner
from app.llm.gemini_client import gemini_client
from app.core.exceptions import ResourceNotFoundException

class JobService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = JobRepository(db)

    def process_job(self, job_id: str, file_path: str):
        job = self.repo.get_job_by_id(job_id)
        if not job:
            return
            
        try:
            job.status = "processing"
            self.db.commit()

            # 1. Data Cleaning & Anomaly Detection
            df = pd.read_csv(file_path)
            job.row_count_raw = len(df)
            
            df = DataCleaner.clean_and_process_dataframe(df)
            df = DataCleaner.detect_anomalies(df)
            job.row_count_clean = len(df)
            self.db.commit()

            # 2. LLM Classification
            uncat_df = df[df['category'] == 'Uncategorised']
            if not uncat_df.empty:
                batch = uncat_df[['txn_id', 'merchant', 'amount', 'currency', 'notes']].to_dict(orient='records')
                classified_batch = gemini_client.classify_transactions_batch(batch)
                class_map = {item['txn_id']: item for item in classified_batch}
                
                def map_llm(row):
                    if row['txn_id'] in class_map:
                        item = class_map[row['txn_id']]
                        return pd.Series([item.get('llm_category'), item.get('llm_failed', False)])
                    return pd.Series([None, False])
                    
                df[['llm_category', 'llm_failed']] = df.apply(map_llm, axis=1)
            else:
                df['llm_category'] = None
                df['llm_failed'] = False

            # 3. Save Transactions to DB
            records = df.to_dict(orient='records')
            db_transactions = []
            for r in records:
                t = Transaction(
                    id=str(uuid.uuid4()),
                    job_id=job_id,
                    txn_id=r.get('txn_id'),
                    date=r.get('date'),
                    merchant=r.get('merchant'),
                    amount=r.get('amount'),
                    currency=r.get('currency'),
                    status=r.get('status'),
                    category=r.get('category'),
                    account_id=r.get('account_id'),
                    is_anomaly=r.get('is_anomaly', False),
                    anomaly_reason=r.get('anomaly_reason'),
                    llm_category=r.get('llm_category'),
                    llm_failed=r.get('llm_failed', False)
                )
                db_transactions.append(t)
                
            self.db.bulk_save_objects(db_transactions)
            
            # 4. Narrative Summary Generation
            total_inr = df[df['currency'] == 'INR']['amount'].sum()
            total_usd = df[df['currency'] == 'USD']['amount'].sum()
            
            top_merchants_series = df.groupby('merchant')['amount'].sum().sort_values(ascending=False).head(3)
            top_merchants = [{"merchant": m, "total": float(v)} for m, v in top_merchants_series.items()]
            
            anomaly_count = int(df['is_anomaly'].sum())
            
            stats = {
                "total_spend_inr": float(total_inr),
                "total_spend_usd": float(total_usd),
                "top_merchants": top_merchants,
                "anomaly_count": anomaly_count
            }
            
            try:
                llm_summary = gemini_client.generate_narrative_summary(stats)
            except Exception:
                llm_summary = {"narrative": "Failed to generate narrative.", "risk_level": "unknown"}
            
            summary = JobSummary(
                job_id=job_id,
                total_spend_inr=float(total_inr),
                total_spend_usd=float(total_usd),
                top_merchants=top_merchants,
                anomaly_count=anomaly_count,
                narrative=llm_summary.get('narrative'),
                risk_level=llm_summary.get('risk_level')
            )
            self.db.add(summary)
            
            job.status = "completed"
            job.completed_at = datetime.datetime.utcnow()
            self.db.commit()

        except Exception as e:
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
