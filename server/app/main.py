from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.db.database import async_engine
from app.api.v1.api_router import api_router
from app.middleware.error_handler import add_exception_handlers
from app.core.limiter import limiter


# ── Application lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic migrations (docker-compose runs `alembic upgrade head`).
    # No create_all() here — this prevents accidental schema drift in production.
    yield
    # Gracefully close all async DB connections on shutdown.
    await async_engine.dispose()


from fastapi.middleware.cors import CORSMiddleware

# ── FastAPI application ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for asynchronous transaction processing and LLM classification",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Wire CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
