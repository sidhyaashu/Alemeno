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
    Full results response per assignment spec:
    - transactions: all cleaned transactions
    - anomalies: flagged anomalous transactions (is_anomaly=True) — explicit separate list
    - summary.category_breakdown: per-category spend breakdown
    - summary.narrative / risk_level: LLM narrative summary
    """
    transactions: List[TransactionBase] = []
    anomalies: List[TransactionBase] = []   # explicit flagged anomalies list

    class Config:
        from_attributes = True


class JobUploadResponseDTO(BaseModel):
    job_id: str
    status: str
