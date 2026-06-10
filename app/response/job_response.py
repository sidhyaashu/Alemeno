from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schema.job import JobSummaryBase, TransactionBase

class JobStatusResponseDTO(BaseModel):
    id: str
    filename: str
    status: str
    row_count_raw: Optional[int]
    row_count_clean: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    summary: Optional[JobSummaryBase] = None

    class Config:
        from_attributes = True

class JobResultsResponseDTO(JobStatusResponseDTO):
    transactions: List[TransactionBase] = []

    class Config:
        from_attributes = True

class JobUploadResponseDTO(BaseModel):
    job_id: str
    status: str
