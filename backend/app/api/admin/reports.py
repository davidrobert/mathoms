"""Admin routes — lista read-only de relatórios + view HTML."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.models.report import Report
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
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AdminReportListResponse:
    reports, total = await list_reports(
        db,
        filter=ListReportsFilter(
            user_id=user_id, workspace_id=workspace_id, limit=limit, offset=offset
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
                owner_email=r.owner_email,
                workspace_name=r.workspace_name,
            )
            for r in reports
        ],
        total=total,
    )


@router.get("/{report_id}/html", response_class=HTMLResponse)
async def view_html(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> HTMLResponse:
    """Serve o HTML do relatório autenticado por ops_session.

    Permite superadmin visualizar sem precisar das credenciais do usuário
    dono do workspace (F7F-Local · ADR-116 — read-only; sem mutação).
    """
    report = (
        await db.execute(select(Report).where(Report.id == report_id))
    ).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report_not_found")
    path = Path(report.html_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="html_missing_on_disk")
    return HTMLResponse(content=path.read_text(encoding="utf-8"))
