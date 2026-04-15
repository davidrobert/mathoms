"""Report endpoints — list and serve HTML reports."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.report import Report
from backend.app.schemas.report import ReportResponse, ReportListResponse

router = APIRouter(prefix="/reports", tags=["reports"])


async def _get_user_workspace(user: User, db: AsyncSession) -> Workspace:
    result = await db.execute(
        select(Workspace).where(Workspace.owner_id == user.id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return ws


def _serialize_report(report: Report) -> ReportResponse:
    """Build ReportResponse with `has_analysis_data` derived from the model (F9)."""
    return ReportResponse(
        id=report.id,
        workspace_id=report.workspace_id,
        title=report.title,
        period=report.period,
        size_bytes=report.size_bytes,
        score=report.score,
        patrimonio_liquido=report.patrimonio_liquido,
        created_at=report.created_at,
        has_analysis_data=bool(report.analysis_json_path),
    )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_user_workspace(current_user, db)
    result = await db.execute(
        select(Report)
        .where(Report.workspace_id == ws.id)
        .order_by(Report.created_at.desc())
    )
    reports = list(result.scalars().all())
    return ReportListResponse(
        reports=[_serialize_report(r) for r in reports],
        total=len(reports),
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_user_workspace(current_user, db)
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == ws.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return _serialize_report(report)


@router.get("/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_user_workspace(current_user, db)
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == ws.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    html_path = Path(report.html_path)
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo HTML não encontrado no disco")

    html_content = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)
