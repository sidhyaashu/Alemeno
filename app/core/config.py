from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Transaction Processing Pipeline"
    API_V1_STR: str = "/api/v1"

    # Sync URL — used by Celery worker (psycopg2)
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/almenodb"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Redis DB 1 for rate limiting — keeps it isolated from Celery (DB 0)
    RATE_LIMIT_REDIS_URL: str = "redis://localhost:6379/1"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

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


settings = Settings()
