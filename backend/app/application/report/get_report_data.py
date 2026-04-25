"""Use case: snapshot E5 JSON do relatório + injeção de lineage/premissas.

ADR-131: lê o ``content_json`` direto do ``pipeline_artifact`` referenciado
por ``Report.analysis_artifact_id`` — zero filesystem.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.application.report._common import fetch_report
from backend.app.services.report_lineage import (
    consumed_documents_for_run,
    lineage_payload,
    workspace_ready_documents_summary,
)


async def get_report_data(workspace_id: str, report_id: str, *, db: AsyncSession) -> JSONResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    artifact = report.analysis_artifact
    if artifact is None or not artifact.content_json:
        raise NotFoundError("Este relatório não tem JSON de análise associado.")

    payload = dict(artifact.content_json)

    doc_total, doc_ids = await workspace_ready_documents_summary(db, workspace_id)
    consumed_total, consumed_ids = await consumed_documents_for_run(db, report.pipeline_run_id)
    payload["_report_lineage"] = lineage_payload(
        pipeline_run_id=report.pipeline_run_id,
        source_document_count=doc_total,
        source_document_ids=doc_ids,
        consumed_document_count=consumed_total,
        consumed_document_ids=consumed_ids,
    )

    # F11.6b — injeta snapshot persistido para a UI (`goals.premissas_snapshot`).
    if report.premissas_snapshot_json:
        snap = report.premissas_snapshot_json
        goals_block = payload.get("goals")
        if isinstance(goals_block, dict):
            payload["goals"] = {**goals_block, "premissas_snapshot": snap}
        else:
            payload["goals"] = {"premissas_snapshot": snap}

    return JSONResponse(content=payload)
