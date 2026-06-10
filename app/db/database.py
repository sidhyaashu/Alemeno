from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

# ── Sync engine ──────────────────────────────────────────────────────────────
# Used by Celery workers — Celery is synchronous and cannot use async sessions.
sync_engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# ── Async engine ─────────────────────────────────────────────────────────────
# Used by FastAPI route handlers — non-blocking I/O via asyncpg driver.
import os
from sqlalchemy.pool import NullPool

extra_args = {}
if os.getenv("TESTING") == "true":
    extra_args["poolclass"] = NullPool
else:
    extra_args["pool_size"] = 10
    extra_args["max_overflow"] = 20

async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,      # detect stale connections
    **extra_args
)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects accessible after commit
)

# ── Shared metadata base ──────────────────────────────────────────────────────
Base = declarative_base()


# ── Dependencies ─────────────────────────────────────────────────────────────

def get_sync_db():
    """Sync session — for Celery workers only."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Backwards-compatible alias so existing worker code doesn't break
get_db = get_sync_db


async def get_async_db():
    """Async session — for FastAPI route handlers."""
    async with AsyncSessionLocal() as session:
        yield session
