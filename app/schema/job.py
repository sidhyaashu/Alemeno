from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class JobSummaryBase(BaseModel):
    total_spend_inr: float
    total_spend_usd: float
    top_merchants: List[Dict[str, Any]]
    anomaly_count: int
    # Per-category spend breakdown — required by assignment
    category_breakdown: Optional[Dict[str, float]] = None
    narrative: Optional[str] = None
    risk_level: Optional[str] = None
    llm_failed: bool = False

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    txn_id: Optional[str] = None
    date: Optional[str] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    account_id: Optional[str] = None
    is_anomaly: bool = False
    anomaly_reason: Optional[str] = None
    llm_category: Optional[str] = None
    llm_failed: bool = False

    class Config:
        from_attributes = True
