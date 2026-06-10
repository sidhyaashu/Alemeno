from typing import Any, Dict, Optional

class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ResourceNotFoundException(AppException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} with id {resource_id} not found.",
            status_code=404
        )

class InvalidFileException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)

class LLMIntegrationException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=502, details=details)
