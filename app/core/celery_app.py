from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"]
)

celery_app.conf.task_routes = {
    "app.worker.tasks.process_transactions_job": "main-queue"
}

# Suppress CPendingDeprecationWarning for Celery 6.0 compatibility
celery_app.conf.broker_connection_retry_on_startup = True
