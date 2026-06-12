from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.db.models import Job
import uuid


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_job_by_id(self, job_id: str, load_relations: bool = False) -> Optional[Job]:
        query = self.db.query(Job).filter(Job.id == job_id)
        if load_relations:
            query = query.options(
                joinedload(Job.summary),
                joinedload(Job.transactions),
            )
        return query.first()

    def create_job(self, filename: str) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            filename=filename,
            status="pending",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs(self, status: Optional[str] = None) -> List[Job]:
        query = self.db.query(Job).options(joinedload(Job.summary))
        if status:
            query = query.filter(Job.status == status)
        return query.order_by(Job.created_at.desc()).all()
