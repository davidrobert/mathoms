"""Helpers privados do agregado Report — serialize + filename sanitize + fetch."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.models.report import Report
from backend.app.schemas.report import ReportResponse


def serialize_report(
    report: Report,
    *,
    source_document_count: int = 0,
    source_document_ids: list[str] | None = None,
) -> ReportResponse:
    ids = source_document_ids if source_document_ids is not None else []
    return ReportResponse(
        id=report.id,
        workspace_id=report.workspace_id,
        title=report.title,
        period=report.period,
        score=report.score,
        patrimonio_liquido=report.patrimonio_liquido,
        created_at=report.created_at,
        pipeline_run_id=report.pipeline_run_id,
        has_analysis_data=report.analysis_artifact_id is not None,
        source_document_count=source_document_count,
        source_document_ids=ids,
        premissas_snapshot=report.premissas_snapshot_json,
    )


def sanitize_filename(raw: str) -> str:
    """Whitelist [A-Za-z0-9._-] para impedir injeção em Content-Disposition."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", raw).strip("._")
    return cleaned or "relatorio.pdf"


async def fetch_report(workspace_id: str, report_id: str, *, db: AsyncSession) -> Report:
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundError("Relatório não encontrado")
    return report
