"""Use case: snapshot E5 JSON do relatório + injeção de lineage/premissas/comparativos.

ADR-131: lê o ``content_json`` direto do ``pipeline_artifact`` referenciado
por ``Report.analysis_artifact_id`` — zero filesystem.

v2.8 (ADR-148): injeta ``comparisons``/``changelog`` top-level via
``SnapshotChangelogBuilder``; primeiro relatório do workspace ⇒ ``null``.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.application.report._common import fetch_report
from backend.app.schemas.snapshot_changelog import (
    changelog_entry_to_read,
    comparison_item_to_read,
)
from backend.app.services.crypto import read_artifact_content
from backend.app.services.report_lineage import (
    consumed_documents_for_run,
    lineage_payload,
    workspace_ready_documents_summary,
)
from backend.app.services.snapshot_pair_loader import load_snapshot_pair
from pipeline.domain.services.snapshot_changelog import build_comparison
from pipeline.domain.types.snapshot_changelog import SnapshotChangelogConfig


async def get_report_data(workspace_id: str, report_id: str, *, db: AsyncSession) -> JSONResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    artifact = report.analysis_artifact
    if artifact is None or not artifact.content_json:
        raise NotFoundError("Este relatório não tem JSON de análise associado.")

    payload = dict(read_artifact_content(artifact.content_json))

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

    # v2.8 (ADR-148): injeta comparisons/changelog via SnapshotChangelogBuilder.
    comparisons, changelog = await _build_snapshot_diff(
        db, workspace_id=workspace_id, current_artifact_id=artifact.id
    )
    payload["comparisons"] = comparisons
    payload["changelog"] = changelog

    return JSONResponse(content=payload)


async def _build_snapshot_diff(
    db: AsyncSession,
    *,
    workspace_id: str,
    current_artifact_id: int,
) -> tuple[list[dict] | None, list[dict] | None]:
    """Carrega par de snapshots e retorna ``(comparisons, changelog)`` JSON-ready."""
    config = SnapshotChangelogConfig()

    def _run(session) -> tuple:
        prev, curr = load_snapshot_pair(
            session,
            workspace_id=workspace_id,
            current_artifact_id=current_artifact_id,
        )
        return build_comparison(prev, curr, config)

    result = await db.run_sync(_run)
    if not result.has_previous:
        return None, None
    items = [comparison_item_to_read(it).model_dump(mode="json") for it in result.items]
    entries = [changelog_entry_to_read(en).model_dump(mode="json") for en in result.entries]
    return items, entries
