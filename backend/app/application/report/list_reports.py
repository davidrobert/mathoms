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


async def list_reports(workspace_id: str, *, db: AsyncSession) -> ReportListResponse:
    result = await db.execute(
        select(Report).where(Report.workspace_id == workspace_id).order_by(Report.created_at.desc())
    )
    reports = list(result.scalars().all())
    doc_total, doc_ids = await workspace_ready_documents_summary(db, workspace_id)
    serialized: list = []
    for r in reports:
        consumed_total, consumed_ids = await consumed_documents_for_run(db, r.pipeline_run_id)
        serialized.append(
            serialize_report(
                r,
                source_document_count=doc_total,
                source_document_ids=doc_ids,
                consumed_document_count=consumed_total,
                consumed_document_ids=consumed_ids,
            )
        )
    return ReportListResponse(reports=serialized, total=len(reports))
