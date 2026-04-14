"""Application settings — loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings


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

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Storage
    STORAGE_DIR: str = "./storage"

    # Pipeline root (for importing existing reports)
    PIPELINE_ROOT: str = str(Path(__file__).resolve().parent.parent.parent.parent)

    model_config = {"env_prefix": "FIN_", "env_file": ".env"}


settings = Settings()
