from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schema.job import JobSummaryBase, TransactionBase


class JobStatusResponseDTO(BaseModel):
    id: str
    filename: str
    status: str
    row_count_raw: Optional[int] = None
    row_count_clean: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    summary: Optional[JobSummaryBase] = None

    class Config:
        from_attributes = True


class JobResultsResponseDTO(JobStatusResponseDTO):
    """
    Full results response. Includes:
    - cleaned transactions list
    - flagged anomalies (is_anomaly=True rows within transactions)
    - per-category spend breakdown (in summary.category_breakdown)
    - LLM narrative summary (in summary.narrative / risk_level)
    """
    transactions: List[TransactionBase] = []

    class Config:
        from_attributes = True


class JobUploadResponseDTO(BaseModel):
    job_id: str
    status: str
