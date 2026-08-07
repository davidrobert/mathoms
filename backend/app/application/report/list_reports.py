"""Use case: lista relatórios do workspace ordenados por ``created_at desc``."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.report._common import serialize_report
from backend.app.models.report import Report
from backend.app.schemas.report import ReportListResponse
from backend.app.services.report_lineage import (
    consumed_documents_for_run,
    workspace_ready_documents_summary,
)
from backend.app.services.report_run_outcome import outcome_for_report, run_outcomes_for


async def _serialize_one(db: AsyncSession, report: Report, *, doc_total, doc_ids, outcomes):
    consumed_total, consumed_ids = await consumed_documents_for_run(db, report.pipeline_run_id)
    return serialize_report(
        report,
        source_document_count=doc_total,
        source_document_ids=doc_ids,
        consumed_document_count=consumed_total,
        consumed_document_ids=consumed_ids,
        run_outcome=outcome_for_report(report.pipeline_run_id, outcomes),
    )


async def list_reports(workspace_id: str, *, db: AsyncSession) -> ReportListResponse:
    result = await db.execute(
        select(Report).where(Report.workspace_id == workspace_id).order_by(Report.created_at.desc())
    )
    reports = list(result.scalars().all())
    doc_total, doc_ids = await workspace_ready_documents_summary(db, workspace_id)
    # 2 queries para a página inteira — não uma por relatório.
    outcomes = await run_outcomes_for(db, [r.pipeline_run_id for r in reports])
    serialized = [
        await _serialize_one(db, r, doc_total=doc_total, doc_ids=doc_ids, outcomes=outcomes)
        for r in reports
    ]
    return ReportListResponse(reports=serialized, total=len(reports))
