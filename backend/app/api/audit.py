"""Audit API — router fino (A6e.4 · ADR-101 R15/R16 · ADR-072).

Audit logs são imutáveis (read-only). Lógica de query vive em
:mod:`backend.app.application.audit`.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.audit import list_audit_logs as _list_audit_logs
from backend.app.application.audit.list_audit_logs import (
    AuditLogEntry,
    AuditLogListResponse,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace
from backend.app.repositories.audit_log_repository import AuditLogRepository

router = APIRouter(
    prefix="/workspaces/{workspace_id}/audit",
    tags=["audit"],
)

__all__ = ["router", "AuditLogEntry", "AuditLogListResponse"]


def _get_repo(db: AsyncSession = Depends(get_db)) -> AuditLogRepository:
    return AuditLogRepository(db)


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None, description="Filtrar por ação exata, ex.: document.upload"),
    workspace: Workspace = Depends(get_current_workspace),
    repo: AuditLogRepository = Depends(_get_repo),
) -> AuditLogListResponse:
    return await _list_audit_logs(workspace.id, repo=repo, limit=limit, action=action)
