"""Use case: snapshot E5 JSON do relatório + injeção de lineage/premissas."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.application.report._common import fetch_report
from backend.app.services.report_lineage import (
    lineage_payload,
    workspace_ready_documents_summary,
)


async def get_report_data(workspace_id: str, report_id: str, *, db: AsyncSession) -> JSONResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    if not report.analysis_json_path:
        raise NotFoundError(
            "Este relatório não tem JSON de análise disponível " "(gerado antes do F9 · ADR-076)."
        )
    json_path = Path(report.analysis_json_path)
    if not json_path.exists():
        raise NotFoundError("Arquivo JSON de análise não encontrado no disco")

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JSON de análise corrompido: {exc}",
        ) from exc

    doc_total, doc_ids = await workspace_ready_documents_summary(db, workspace_id)
    payload["_report_lineage"] = lineage_payload(
        pipeline_run_id=report.pipeline_run_id,
        source_document_count=doc_total,
        source_document_ids=doc_ids,
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
