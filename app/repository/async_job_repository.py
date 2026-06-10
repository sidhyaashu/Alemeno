from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job


class AsyncJobRepository:
    """
    Async repository for FastAPI route handlers.
    All methods are coroutines — must be awaited.
    The Celery worker uses the separate (sync) JobRepository.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_job_by_id(
        self, job_id: str, load_relations: bool = False
    ) -> Optional[Job]:
        stmt = select(Job).where(Job.id == job_id)
        if load_relations:
            stmt = stmt.options(
                selectinload(Job.summary),
                selectinload(Job.transactions),
            )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_job(self, filename: str) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            filename=filename,
            status="pending",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def list_jobs(self, status: Optional[str] = None) -> List[Job]:
        stmt = select(Job).options(selectinload(Job.summary))
        if status:
            stmt = stmt.where(Job.status == status)
        stmt = stmt.order_by(Job.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
