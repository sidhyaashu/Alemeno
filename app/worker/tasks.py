from celery import shared_task
from app.db.database import SessionLocal
from app.services.job_service import JobService

@shared_task(name="app.worker.tasks.process_transactions_job")
def process_transactions_job(job_id: str, file_path: str):
    db = SessionLocal()
    try:
        service = JobService(db)
        service.process_job(job_id, file_path)
    finally:
        db.close()
