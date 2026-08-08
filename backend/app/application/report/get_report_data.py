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
from backend.app.core.logging import get_logger
from backend.app.schemas.snapshot_changelog import (
    changelog_entry_to_read,
    comparison_item_to_read,
)
from backend.app.services.report_lineage import (
    consumed_documents_for_run,
    lineage_payload,
    workspace_ready_documents_summary,
)
from backend.app.services.security.crypto import read_artifact_content
from backend.app.services.snapshot_pair_loader import load_snapshot_pair
from pipeline.artifact_store import stage_aliases
from pipeline.domain.services.snapshot_changelog import build_comparison
from pipeline.domain.types.snapshot_changelog import SnapshotChangelogConfig

logger = get_logger(__name__)

# `E5` e `analyze_finances` são o mesmo stage (ADR-093).
_ANALYSIS_STAGES = frozenset(stage_aliases("analyze_finances"))


async def get_report_data(workspace_id: str, report_id: str, *, db: AsyncSession) -> JSONResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    artifact = report.analysis_artifact
    if artifact is None or not artifact.content_json:
        raise NotFoundError("Este relatório não tem JSON de análise associado.")
    _assert_analysis_stage(report_id, artifact)

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
    # v3 (ADR-190 §Emenda): + períodos reais do par para a moldura temporal da V0.
    comparisons, changelog, periods = await _build_snapshot_diff(
        db, workspace_id=workspace_id, current_artifact_id=artifact.id
    )
    payload["comparisons"] = comparisons
    payload["changelog"] = changelog
    payload["comparison_periods"] = periods

    return JSONResponse(content=payload)


# Nada no schema afirma que `analysis_artifact_id` é um artefato de análise: a
# FK aceita qualquer row de `pipeline_artifacts`, o write-path acerta por
# construção e o read-path aceitava o que viesse. No DB de dogfood 21 relatórios
# apontavam para E2/E3/E1.5a e eram servidos com HTTP 200 (ADR-371). O 404 é o
# efeito; o sinal é o log — ausência calada seria só outra corrupção calada.
def _assert_analysis_stage(report_id: str, artifact) -> None:
    """404 + log quando a FK aponta para artefato que não é de análise."""
    if artifact.stage in _ANALYSIS_STAGES:
        return
    logger.error(
        "report.analysis_artifact_stage_mismatch",
        extra={
            "report_id": report_id,
            "artifact_id": artifact.id,
            "stage_encontrado": artifact.stage,
            "stages_esperados": sorted(_ANALYSIS_STAGES),
        },
    )
    raise NotFoundError("A análise deste relatório não está mais disponível.")


async def _build_snapshot_diff(
    db: AsyncSession,
    *,
    workspace_id: str,
    current_artifact_id: int,
) -> tuple[list[dict] | None, list[dict] | None, dict[str, str] | None]:
    """Retorna ``(comparisons, changelog, comparison_periods)`` JSON-ready."""
    config = SnapshotChangelogConfig()

    def _run(session) -> tuple:
        prev, curr = load_snapshot_pair(
            session,
            workspace_id=workspace_id,
            current_artifact_id=current_artifact_id,
        )
        return build_comparison(prev, curr, config), prev, curr

    result, prev, curr = await db.run_sync(_run)
    if not result.has_previous:
        return None, None, None
    items = [comparison_item_to_read(it).model_dump(mode="json") for it in result.items]
    entries = [changelog_entry_to_read(en).model_dump(mode="json") for en in result.entries]
    return items, entries, _periods_payload(prev, curr)


def _periods_payload(prev, curr) -> dict[str, str] | None:
    if prev is None or not prev.period_yyyymm or not curr.period_yyyymm:
        return None
    return {"current": curr.period_yyyymm, "previous": prev.period_yyyymm}
