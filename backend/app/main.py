"""Fin API — FastAPI application entry point."""

import os
from pathlib import Path

# Before any import of scripts.* (e0_route → pipeline_common): workspace path model.
_repo_root = Path(__file__).resolve().parent.parent.parent
os.environ.setdefault("FIN_WORKSPACE_ROOT", str(_repo_root))

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.auth import router as auth_router
from backend.app.api.reports import router as reports_router
from backend.app.api.vault import router as vault_router
from backend.app.api.documents import router as documents_router
from backend.app.api.pipeline import router as pipeline_router
from backend.app.api.config import router as config_router
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url=f"{settings.API_PREFIX}/docs",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(reports_router, prefix=settings.API_PREFIX)
app.include_router(vault_router, prefix=settings.API_PREFIX)
app.include_router(documents_router, prefix=settings.API_PREFIX)
app.include_router(pipeline_router, prefix=settings.API_PREFIX)
app.include_router(config_router, prefix=settings.API_PREFIX)
app.include_router(llm_router, prefix=settings.API_PREFIX)
app.include_router(ws_router, prefix=settings.API_PREFIX)
app.include_router(transactions_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)
app.include_router(notifications_router, prefix=settings.API_PREFIX)
app.include_router(audit_router, prefix=settings.API_PREFIX)
app.include_router(goals_router, prefix=settings.API_PREFIX)
app.include_router(workspaces_router, prefix=settings.API_PREFIX)
app.include_router(workspaces_tenant_router, prefix=settings.API_PREFIX)
app.include_router(invitations_router, prefix=settings.API_PREFIX)
app.include_router(tasks_router, prefix=settings.API_PREFIX)
app.include_router(feature_flags_router, prefix=settings.API_PREFIX)


@app.get("/health")
async def health():
    """Health check — reports Redis, Celery worker, and DB status."""
    checks = {"api": "ok", "version": "0.6.0"}

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

    overall = "ok" if all(v == "ok" for k, v in checks.items() if k not in ("version",)) else "degraded"
    checks["status"] = overall

    return checks
