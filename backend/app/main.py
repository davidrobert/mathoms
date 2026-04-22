"""Mathoms AI — FastAPI application entry point."""

import os
from pathlib import Path

# Before any import of scripts.* (e0_route → pipeline_common): workspace path model.
_repo_root = Path(__file__).resolve().parent.parent.parent
os.environ.setdefault("MATHOMS_WORKSPACE_ROOT", str(_repo_root))

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError as DomainValidationError,
)
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.logging import setup_logging
from backend.app.core.otel import instrument_fastapi, setup_otel
from backend.app.middleware.correlation import CorrelationIdMiddleware
from backend.app.middleware.legacy_deprecation import LegacyApiDeprecationMiddleware
from backend.app.api.auth import router as auth_router
from backend.app.api.reports import router as reports_router
from backend.app.api.vault import router as vault_router
from backend.app.api.documents import router as documents_router
from backend.app.api.pipeline import router as pipeline_router
from backend.app.api.categories import router as categories_router
from backend.app.api.config import router as config_router
from backend.app.api.family_members import router as family_members_router
from backend.app.api.llm import router as llm_router
from backend.app.api.ws import router as ws_router
from backend.app.api.transactions import router as transactions_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.notifications import router as notifications_router
from backend.app.api.audit import router as audit_router
from backend.app.api.goals import router as goals_router
from backend.app.api.workspaces import (
    router as workspaces_router,
    tenant_router as workspaces_tenant_router,
)
from backend.app.api.invitations import router as invitations_router
from backend.app.api.tasks import router as tasks_router
from backend.app.api.feature_flags import router as feature_flags_router
from backend.app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)


setup_logging()
setup_otel(service_name="mathoms-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    instrument_fastapi(app)
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url=f"{settings.API_PREFIX}/docs",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    servers=[{"url": settings.API_PREFIX, "description": "Canonical v1"}],
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(LegacyApiDeprecationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# A6e.3 · ADR-101 R15 — use cases levantam erros de domínio tipados;
# tradução para HTTP acontece aqui, não em cada router.
@app.exception_handler(NotFoundError)
async def _handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def _handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(DomainValidationError)
async def _handle_validation(
    request: Request, exc: DomainValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# A6e.5 · ADR-108 — cada router é registrado 2×:
#   1. canônico em settings.API_PREFIX (/api/v1) — aparece no OpenAPI
#   2. legado em settings.LEGACY_API_PREFIX (/api) — alias deprecated,
#      include_in_schema=False para não poluir o snapshot. Remoção em F7A.
_ALL_ROUTERS = (
    auth_router,
    reports_router,
    vault_router,
    documents_router,
    pipeline_router,
    config_router,
    family_members_router,
    categories_router,
    llm_router,
    ws_router,
    transactions_router,
    dashboard_router,
    notifications_router,
    audit_router,
    goals_router,
    workspaces_router,
    workspaces_tenant_router,
    invitations_router,
    tasks_router,
    feature_flags_router,
)

for _router in _ALL_ROUTERS:
    app.include_router(_router, prefix=settings.API_PREFIX)

for _router in _ALL_ROUTERS:
    app.include_router(
        _router,
        prefix=settings.LEGACY_API_PREFIX,
        include_in_schema=False,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> dict:
    """Health check — reports Redis, Celery worker, and DB status."""
    checks: dict = {"api": "ok", "version": "0.6.0"}

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        checks["redis"] = "ok"
        await r.close()
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    try:
        from backend.app.worker import celery_app
        inspect = celery_app.control.inspect(timeout=2.0)
        active = inspect.active()
        checks["celery"] = "ok" if active else "no_workers"
    except Exception as exc:
        checks["celery"] = f"error: {exc}"

    try:
        from backend.app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # A6b (ADR-106): indica o modo de artefatos ativo (global).
    # Por workspace usa _resolve_use_db_artifacts — aqui reporta o default global.
    checks["artifact_store_mode"] = "db" if settings.USE_DB_ARTIFACTS else "disk"

    # A6f.1 (ADR-112): pipeline-service HTTP boundary. URL só aparece quando
    # setada (cutover HTTP); ausente = InProcessPipelineClient em uso.
    pipeline_service_url = os.environ.get("MATHOMS_PIPELINE_SERVICE_URL", "").strip()
    checks["pipeline_service_url"] = pipeline_service_url or None
    checks["pipeline_service_reachable"] = (
        await _probe_pipeline_service(pipeline_service_url)
        if pipeline_service_url
        else None
    )

    informational = {"version", "artifact_store_mode", "pipeline_service_url",
                     "pipeline_service_reachable"}
    overall = "ok" if all(
        v == "ok" for k, v in checks.items() if k not in informational
    ) else "degraded"
    checks["status"] = overall

    return checks


async def _probe_pipeline_service(url: str) -> bool:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as http:
            r = await http.get(f"{url.rstrip('/')}/health")
            return r.status_code == 200
    except Exception:
        return False
