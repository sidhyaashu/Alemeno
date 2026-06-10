from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.db.database import async_engine
from app.api.v1.api_router import api_router
from app.middleware.error_handler import add_exception_handlers


# ── Rate limiter (Redis-backed) ───────────────────────────────────────────────
# Uses Redis DB 1 so rate limit keys are isolated from Celery task data (DB 0).
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_REDIS_URL,
)


# ── Application lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic migrations (docker-compose runs `alembic upgrade head`).
    # No create_all() here — this prevents accidental schema drift in production.
    yield
    # Gracefully close all async DB connections on shutdown.
    await async_engine.dispose()


# ── FastAPI application ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for asynchronous transaction processing and LLM classification",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Wire rate limiter into the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global exception handlers
add_exception_handlers(app)

# API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}
