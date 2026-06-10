from celery import shared_task
from app.db.database import SessionLocal
from app.services.job_service import JobService

@shared_task(
    name="app.worker.tasks.process_transactions_job",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_kwargs={"max_retries": 3},
)
def process_transactions_job(self, job_id: str, file_ref: str, storage_type: str = "local", gemini_api_key: str = None):
    db = SessionLocal()
    try:
        service = JobService(db)
        service.process_job(job_id, file_ref, storage_type=storage_type, gemini_api_key=gemini_api_key)
    finally:
        db.close()

