"""Application settings — loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Mathoms AI"
    # A6e.5 · ADR-108 — rotas canônicas sob /api/v1.
    # Alias legado /api continua funcional via LegacyApiDeprecationMiddleware
    # até F7A (remoção planejada quando reverse proxy estiver pronto).
    API_PREFIX: str = "/api/v1"
    LEGACY_API_PREFIX: str = "/api"
    API_VERSION: str = "1.0.0"
    LEGACY_SUNSET_DATE: str = "TBD F7A"
    DEBUG: bool = True

    # Auth
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    ALGORITHM: str = "HS256"

    # 7B.13 — brute-force lockout em /auth/login. Cooldown escalonado por
    # e-mail; contador em Redis (ADR-111). Override via env para tuning.
    BRUTE_FORCE_THRESHOLD: int = 5
    BRUTE_FORCE_LOCKOUT_DURATIONS_S: list[int] = [60, 300, 900, 3600]  # 1m → 5m → 15m → 1h

    # Database (SQLite for dev, PostgreSQL for prod).
    # F6.5E.4: default usa caminho ABSOLUTO derivado de _PROJECT_ROOT para
    # eliminar ambiguidade de cwd (mesmo bug que motivou o guard em
    # backend/alembic/env.py). Em prod sempre setar MATHOMS_DATABASE_URL.
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'mathoms.db'}"

    # Redis broker (Celery + result backend). Em produção deve apontar para
    # instância com policy `noeviction` — eviction LRU evicta mensagens da
    # fila como se fossem cache, perdendo jobs silenciosamente.
    REDIS_URL: str = "redis://localhost:6379/0"

    # Redis cache (Pub/Sub + pipeline progress + ephemeral cache). Em produção
    # aponta para instância separada com policy `allkeys-lru`. Em dev/teste
    # default coincide com REDIS_URL (mesmo Redis serve broker e cache).
    # Reading order: setting explícita > REDIS_URL.
    REDIS_CACHE_URL: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Storage — per-tenant file storage root
    STORAGE_ROOT: Path = _PROJECT_ROOT / "storage"

    # Pipeline root (project root, for config/ and existing reports)
    PIPELINE_ROOT: Path = _PROJECT_ROOT

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_STORAGE_PER_WORKSPACE_MB: int = 500
    MAX_UPLOAD_BATCH_SIZE: int = 150

    # Vault encryption (Fernet symmetric key). Generate via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY: str = ""

    # Fase 2 · ADR-083: quando True, o pipeline web usa DBArtifactStore (banco)
    # em vez de DiskArtifactStore. Default flipado para True (cutover concluído);
    # override por workspace via `workspaces.use_db_artifacts_override`.
    USE_DB_ARTIFACTS: bool = True

    # ADR-115 · A6e.events: quando True, handler reativo para TaskCreated/
    # Updated cria Notification na transação do use case. Enquanto False
    # (default), o cron ``scan_and_create_notifications`` continua sendo
    # fonte única — coexistência segura durante validação em produção.
    # Remover o cron + flag após gate humano verde (A6e.events-followup).
    USE_EVENT_DRIVEN_TASK_NOTIFICATIONS: bool = False

    # F7F-Local / ADR-116 — console interno (/admin/*).
    # Default off: rotas só montam se `MATHOMS_INTERNAL_OPS_UI_ENABLED=1`.
    # Bloqueia boot em `ENVIRONMENT=production` a menos que
    # `MATHOMS_INTERNAL_OPS_ACCEPT_PRODUCTION_RISK=1` seja setada
    # explicitamente — console local (IA-0) não deve rodar em prod.
    INTERNAL_OPS_UI_ENABLED: bool = False
    INTERNAL_OPS_ACCEPT_PRODUCTION_RISK: bool = False
    ENVIRONMENT: str = "development"

    # env_file resolvido em ABSOLUTO e com múltiplas localizações — evita que o
    # backend carregue config diferente conforme cwd (bug onde `.env` em
    # `backend/.env` não era lido quando uvicorn rodava da raiz do repo).
    # Ordem de precedência: raiz do repo > backend/.
    model_config = {
        "env_prefix": "MATHOMS_",
        "env_file": (
            str(_PROJECT_ROOT / ".env"),
            str(_PROJECT_ROOT / "backend" / ".env"),
        ),
        # Variáveis de ambiente desconhecidas (ex: stale vars com prefixo MATHOMS_)
        # são ignoradas silenciosamente em vez de causar ValidationError.
        "extra": "ignore",
    }

    @property
    def sync_database_url(self) -> str:
        """Sync DB URL for background threads (replace async driver)."""
        return self.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")

    @property
    def cache_redis_url(self) -> str:
        """Resolve Redis URL para cache/pubsub; default cai no broker em dev."""
        return self.REDIS_CACHE_URL or self.REDIS_URL


settings = Settings()
