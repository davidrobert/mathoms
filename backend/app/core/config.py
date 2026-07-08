"""Application settings — loaded from environment variables."""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# W1-T05 · Production hardening: rejeita defaults conhecidamente
# inseguros em ambiente prod. Lista é small e explícita — qualquer
# string genérica de exemplo deve ser adicionada.
_INSECURE_SECRET_DEFAULTS: frozenset[str] = frozenset(
    {
        "dev-secret-key-change-in-production",
        "change-me",
        "secret",
    }
)
_MIN_PROD_SECRET_LEN = 32

# P0-4 (SEC-06) — chaves Fernet públicas-por-design no repo (compose dev +
# CI/nightly). Em produção cifrariam BYOK/dado real com chave conhecida; o
# fail-fast de boot fecha o cenário "subiu prod esquecendo de trocar a env".
# Valor vazio já é barrado em uso por vault.py; aqui barramos os defaults conhecidos.
_INSECURE_FERNET_DEFAULTS: frozenset[str] = frozenset(
    {
        "03RkjFvWj5Bd2oPYr65XbcZosiu15kPdl8acj9H_OYg=",  # docker-compose.dev.yml
        "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=",  # ci.yml / nightly.yml  # gitleaks:allow
    }
)


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

    # ADR-170 (W3-T03) — refresh flow. Default off até frontend mergear +
    # 1 release estável; quando off, comportamento ADR-057 legado (access 24h,
    # sem cookie) fica intacto. Env: MATHOMS_AUTH_REFRESH_FLOW.
    AUTH_REFRESH_FLOW: bool = False
    AUTH_REFRESH_ACCESS_TTL_MINUTES: int = 15
    AUTH_REFRESH_TTL_DAYS: int = 7  # sliding por rotação
    AUTH_REFRESH_ABSOLUTE_CAP_DAYS: int = 30  # teto via created_at (emenda ADR-170)
    AUTH_REFRESH_GRACE_WINDOW_S: int = 60  # anti-falso-positivo de reuse (2 tabs)
    # Secure por config explícita, nunca por request.scheme — TLS termina no
    # Traefik e o backend vê http interno. Override False só em dev local.
    AUTH_COOKIE_SECURE: bool = True

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

    # W1-T04 · PDF render concurrency cap. Playwright consome ~200MB de RAM
    # por renderização (Chromium headless). Sem limite, 4+ PDFs simultâneos
    # em CX32 (8GB) garantem OOM. Default 2 protege CX32 mantendo throughput
    # razoável; range 1-8 cobre dev até produção dimensionada.
    # Enforçado via asyncio.Semaphore singleton em pdf_renderer (ADR-111
    # categoria b — recurso local idempotente).
    MATHOMS_PDF_CONCURRENCY: int = Field(default=2, ge=1, le=8)

    # Vault encryption (Fernet symmetric key). Generate via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY: str = ""

    # ADR-171 — janela de rotação: CSV "key_nova,key_antiga". Primeira =
    # primária (encrypt); demais decrypt-only. Quando setada, tem precedência
    # sobre FERNET_KEY. Fora de rotação, deixe vazia e use FERNET_KEY single.
    FERNET_KEYS: str = ""

    # W4-T04 / SR-018 — overrides de rate limit no formato "N/window_s"
    # (ex.: "10/60"). Vazio = default de backend/app/services/security/rate_limit.py.
    RATE_LIMIT_LOGIN: str = ""
    RATE_LIMIT_UPLOAD: str = ""
    RATE_LIMIT_PIPELINE_RUN: str = ""
    RATE_LIMIT_CPF_VIEW_FULL: str = ""

    # ADR-231 — encryption at-rest de PII em pipeline_artifacts.content_json.
    # Default True: writes via DBArtifactStore aplicam Fernet encrypt após
    # schema validation. Reads sempre decriptam sentinel detectado (compat
    # com rows antigas em revert). False bypassa apenas o encrypt em writes
    # novos — kill switch operacional, não desencripta histórico.
    ENCRYPT_PIPELINE_ARTIFACTS: bool = True

    # ADR-115 · A6e.events: quando True, handler reativo para TaskCreated/
    # Updated cria Notification na transação do use case. Enquanto False
    # (default), o cron ``scan_and_create_notifications`` continua sendo
    # fonte única — coexistência segura durante validação em produção.
    # Remover o cron + flag após gate humano verde (A6e.events-followup).
    USE_EVENT_DRIVEN_TASK_NOTIFICATIONS: bool = False

    # ADR-199 (PLANNER_REVIEW Ato 4) — parecer planejador holístico.
    # Stage `review_finances_holistic` executa para todos os workspaces.
    # Promovido a True em 2026-05-14 (Ato 6) por decisão do owner — feature
    # liberada para todos os workspaces premium; free tier recebe payload
    # gated via tier_filter (ADR-208). Override por env var
    # MATHOMS_ENABLE_PARECER_PLANEJADOR=false como kill-switch operacional.
    ENABLE_PARECER_PLANEJADOR: bool = True

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

    # W1-T05 · Production fail-fast (SR-022 / SR-021). Em
    # ENVIRONMENT=production rejeita: SECRET_KEY em lista de defaults
    # inseguros (JWT seria forjável), SECRET_KEY com <32 chars (entropia
    # insuficiente HS256), DATABASE_URL com sqlite (driver não tolera prod
    # multi-worker).
    @model_validator(mode="after")
    def _enforce_prod_invariants(self) -> "Settings":
        """W1-T05 · Production fail-fast (SR-022 / SR-021)."""
        if self.ENVIRONMENT != "production":
            return self
        if self.SECRET_KEY in _INSECURE_SECRET_DEFAULTS:
            raise RuntimeError("SECRET_KEY must not use a development default in production")
        if len(self.SECRET_KEY) < _MIN_PROD_SECRET_LEN:
            raise RuntimeError(
                f"SECRET_KEY must be ≥{_MIN_PROD_SECRET_LEN} chars in production "
                f"(got {len(self.SECRET_KEY)})"
            )
        if "sqlite" in (self.DATABASE_URL or "").lower():
            raise RuntimeError("DATABASE_URL must not use sqlite in production")
        self._reject_insecure_fernet_keys()
        return self

    def _reject_insecure_fernet_keys(self) -> None:
        if self.FERNET_KEY in _INSECURE_FERNET_DEFAULTS:
            raise RuntimeError("FERNET_KEY must not use a development/CI default in production")
        for rotation_key in self.FERNET_KEYS.split(","):
            if rotation_key.strip() in _INSECURE_FERNET_DEFAULTS:
                raise RuntimeError(
                    "FERNET_KEYS must not include a development/CI default in production"
                )

    @property
    def sync_database_url(self) -> str:
        """Sync DB URL for the Celery task layer — psycopg3 driver explícito (ADR-253)."""
        # postgresql+asyncpg:// → postgresql+psycopg:// (psycopg v3). Sem o driver
        # explícito o SQLAlchemy cairia no default (psycopg2), removido em A20.L8.
        # sqlite+aiosqlite:// → sqlite:// (driver pysqlite default em testes).
        return self.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg")

    @property
    def cache_redis_url(self) -> str:
        """Resolve Redis URL para cache/pubsub; default cai no broker em dev."""
        return self.REDIS_CACHE_URL or self.REDIS_URL


settings = Settings()
