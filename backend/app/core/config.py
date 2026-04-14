"""Application settings — loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fin API"
    API_PREFIX: str = "/api"
    DEBUG: bool = True

    # Auth
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    ALGORITHM: str = "HS256"

    # Database (SQLite for dev, PostgreSQL for prod)
    DATABASE_URL: str = "sqlite+aiosqlite:///./fin.db"

    # Redis (Celery broker + result backend + Pub/Sub)
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Storage — per-tenant file storage root
    STORAGE_ROOT: Path = _PROJECT_ROOT / "storage"

    # Pipeline root (project root, for config/ and existing reports)
    PIPELINE_ROOT: Path = _PROJECT_ROOT

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_STORAGE_PER_WORKSPACE_MB: int = 500
    MAX_UPLOAD_BATCH_SIZE: int = 20

    # Vault encryption (Fernet symmetric key). Generate via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY: str = ""

    model_config = {"env_prefix": "FIN_", "env_file": ".env"}

    @property
    def sync_database_url(self) -> str:
        """Sync DB URL for background threads (replace async driver)."""
        return self.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")


settings = Settings()
