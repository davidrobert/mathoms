"""Admin routes — lista read-only de relatórios."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.schemas.admin import (
    AdminReportListResponse,
    ReportSummaryDTO,
)
from backend.app.services.internal_ops import ListReportsFilter, list_reports

router = APIRouter(prefix="/reports")


@router.get("", response_model=AdminReportListResponse)
async def list_(
    user_id: str | None = Query(default=None),
    workspace_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AdminReportListResponse:
    reports = await list_reports(
        db,
        filter=ListReportsFilter(
            user_id=user_id, workspace_id=workspace_id, limit=limit
        ),
    )
    return AdminReportListResponse(
        reports=[
            ReportSummaryDTO(
                id=r.id,
                workspace_id=r.workspace_id,
                title=r.title,
                period=r.period,
                created_at=r.created_at,
                size_bytes=r.size_bytes,
            )
            for r in reports
        ]
    )
