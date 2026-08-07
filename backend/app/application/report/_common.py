"""Helpers privados do agregado Report — serialize + filename sanitize + fetch."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.models.report import Report
from backend.app.schemas.report import ReportResponse
from backend.app.services.report_run_outcome import ReportRunOutcome


def serialize_report(
    report: Report,
    *,
    source_document_count: int = 0,
    source_document_ids: list[str] | None = None,
    consumed_document_count: int = 0,
    consumed_document_ids: list[str] | None = None,
    workspace_family_surname: str | None = None,
    run_outcome: ReportRunOutcome,
) -> ReportResponse:
    ids = source_document_ids if source_document_ids is not None else []
    consumed_ids = consumed_document_ids if consumed_document_ids is not None else []
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
        consumed_document_count=consumed_document_count,
        consumed_document_ids=consumed_ids,
        premissas_snapshot=report.premissas_snapshot_json,
        workspace_family_surname=workspace_family_surname,
        run_outcome=run_outcome,
    )


def sanitize_filename(raw: str) -> str:
    """Whitelist [A-Za-z0-9._-] para impedir injeção em Content-Disposition."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", raw).strip("._")
    return cleaned or "relatorio.pdf"


def slugify_family(surname: str | None) -> str:
    """ASCII-safe slug: NFKD fold, lowercase, hífen como separador (vazio se inválido)."""
    if not surname:
        return ""
    s = unicodedata.normalize("NFKD", surname.strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def extract_period_yyyymm(period: str | None) -> str:
    """Extrai ``YYYY-MM`` final (ex.: ``"2023-01 a 2026-04"`` → ``"2026-04"``)."""
    if not period:
        return ""
    matches = re.findall(r"(\d{4}-\d{2})", period)
    return matches[-1] if matches else ""


def compose_pdf_filename(
    surname: str | None,
    period: str | None,
    generated_at: datetime,
) -> str:
    """Compõe ``mathoms-planejamento-{slug}-{YYYY-MM}.pdf`` (v2.F.3c · §17.8.c)."""
    slug = slugify_family(surname)
    yyyymm = extract_period_yyyymm(period) or generated_at.strftime("%Y-%m")
    if slug:
        return f"mathoms-planejamento-{slug}-{yyyymm}.pdf"
    return f"mathoms-planejamento-{yyyymm}.pdf"


async def fetch_report(workspace_id: str, report_id: str, *, db: AsyncSession) -> Report:
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundError("Relatório não encontrado")
    return report
