from typing import Any, Dict, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    status_code: int
    details: Optional[Dict[str, Any]] = None
