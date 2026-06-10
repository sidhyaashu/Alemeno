from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# ── Rate limiter (Redis-backed) ───────────────────────────────────────────────
# Uses Redis DB 1 so rate limit keys are isolated from Celery task data (DB 0).
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_REDIS_URL,
)
