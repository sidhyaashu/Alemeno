from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Transaction Processing Pipeline"
    API_V1_STR: str = "/api/v1"

    # Sync URL — used by Celery worker (psycopg2)
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/almenodb"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Redis DB 1 for rate limiting — isolated from Celery (DB 0)
    RATE_LIMIT_REDIS_URL: str = "redis://localhost:6379/1"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ── Cloudflare R2 (S3-compatible object storage) ─────────────────────────
    # If these are set, uploaded CSVs are stored in R2 instead of local disk.
    # Leave blank to fall back to local disk storage (default for local dev).
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Async URL for FastAPI routes (asyncpg driver)."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        return url

    @property
    def R2_CONFIGURED(self) -> bool:
        """True if all four R2 credentials are present."""
        return all([
            self.R2_ACCOUNT_ID,
            self.R2_ACCESS_KEY_ID,
            self.R2_SECRET_ACCESS_KEY,
            self.R2_BUCKET_NAME,
        ])


settings = Settings()
