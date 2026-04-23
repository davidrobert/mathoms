"""Console interno — agregador de routers /admin/* (ADR-116).

Montado em `backend/app/main.py` só quando `settings.INTERNAL_OPS_UI_ENABLED`
é True. Rotas NÃO entram no prefixo canônico `/api/v1` — vivem em `/admin/*`
(internal, não versionado).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.admin.documents import router as documents_router
from backend.app.api.admin.login import router as login_router
from backend.app.api.admin.metrics import router as metrics_router
from backend.app.api.admin.reports import router as reports_router
from backend.app.api.admin.users import router as users_router
from backend.app.core.config import settings


def _require_ui_enabled() -> None:
    if not settings.INTERNAL_OPS_UI_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(_require_ui_enabled)])
router.include_router(login_router)
router.include_router(users_router)
router.include_router(documents_router)
router.include_router(metrics_router)
router.include_router(reports_router)

__all__ = ["router"]
