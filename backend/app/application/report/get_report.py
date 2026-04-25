"""Use case: lê um Report por id (404 via NotFoundError)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.report._common import fetch_report, serialize_report
from backend.app.schemas.report import ReportResponse
from backend.app.services.report_lineage import (
    consumed_documents_for_run,
    workspace_ready_documents_summary,
)


async def get_report(workspace_id: str, report_id: str, *, db: AsyncSession) -> ReportResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    doc_total, doc_ids = await workspace_ready_documents_summary(db, workspace_id)
    consumed_total, consumed_ids = await consumed_documents_for_run(db, report.pipeline_run_id)
    return serialize_report(
        report,
        source_document_count=doc_total,
        source_document_ids=doc_ids,
        consumed_document_count=consumed_total,
        consumed_document_ids=consumed_ids,
    )
