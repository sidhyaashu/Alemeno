"""
Pytest configuration — set up test environment so imports work correctly.
Tests that hit the API use TestClient which runs in-process (no real server needed).
Tests that hit the DB are skipped here — they require docker compose to be running.
"""
import os

os.environ["TESTING"] = "true"

# Point to a test DB / use SQLite in-memory so unit tests don't need PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("RATE_LIMIT_REDIS_URL", "memory://")
os.environ.setdefault("GEMINI_API_KEY", "")
