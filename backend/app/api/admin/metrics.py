"""Admin routes — métricas + audit."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.schemas.admin import (
    AuditEntryDTO,
    AuditListResponse,
    MetricsResponse,
)
from backend.app.services.internal_ops import get_metrics
from backend.app.services.internal_ops.audit import read_audit

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(
    period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> MetricsResponse:
    snap = await get_metrics(db, period_days=period_days)
    return MetricsResponse(
        users_total=snap.users_total,
        users_active=snap.users_active,
        workspaces_total=snap.workspaces_total,
        documents_total=snap.documents_total,
        documents_needs_review=snap.documents_needs_review,
        storage_bytes_total=snap.storage_bytes_total,
        pipeline_runs_total=snap.pipeline_runs_total,
        pipeline_runs_last_period=snap.pipeline_runs_last_period,
        period_days=snap.period_days,
        generated_at=snap.generated_at,
    )


@router.get("/audit", response_model=AuditListResponse)
async def audit(
    limit: int = Query(default=200, ge=1, le=2000),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AuditListResponse:
    entries = read_audit(limit=limit)
    return AuditListResponse(
        entries=[AuditEntryDTO(**e) for e in entries]
    )
