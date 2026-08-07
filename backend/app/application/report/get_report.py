"""Use case: lê um Report por id (404 via NotFoundError)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.report._common import fetch_report, serialize_report
from backend.app.models.workspace import Workspace
from backend.app.schemas.report import ReportResponse
from backend.app.services.report_lineage import (
    consumed_documents_for_run,
    workspace_ready_documents_summary,
)
from backend.app.services.report_run_outcome import outcome_for_report, run_outcomes_for


async def get_report(workspace_id: str, report_id: str, *, db: AsyncSession) -> ReportResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    doc_total, doc_ids = await workspace_ready_documents_summary(db, workspace_id)
    consumed_total, consumed_ids = await consumed_documents_for_run(db, report.pipeline_run_id)
    surname = (
        await db.execute(select(Workspace.family_surname).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()
    outcomes = await run_outcomes_for(db, [report.pipeline_run_id])
    return serialize_report(
        report,
        run_outcome=outcome_for_report(report.pipeline_run_id, outcomes),
        source_document_count=doc_total,
        source_document_ids=doc_ids,
        consumed_document_count=consumed_total,
        consumed_document_ids=consumed_ids,
        workspace_family_surname=surname,
    )
