import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import AppException
from app.response.standard_response import ErrorResponse

logger = logging.getLogger(__name__)

def add_exception_handlers(app):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(f"AppException: {exc.message}")
        response = ErrorResponse(
            error=exc.message,
            status_code=exc.status_code,
            details=exc.details
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(exclude_none=True)
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
        response = ErrorResponse(
            error="Internal Server Error",
            status_code=500
        )
        return JSONResponse(
            status_code=500,
            content=response.model_dump(exclude_none=True)
        )
