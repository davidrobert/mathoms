"""F11.4a — linhagem de documentos do relatório (workspace agregado vs run consumida)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import DOCUMENT_CLASSIFIED_OK, Document
from backend.app.models.pipeline_artifact import PipelineArtifact


async def workspace_ready_documents_summary(
    db: AsyncSession, workspace_id: str, *, id_limit: int = 128
) -> tuple[int, list[str]]:
    """Conta documentos classificados (ready/processed) e devolve até *id_limit* UUIDs."""
    count_stmt = (
        select(func.count())
        .select_from(Document)
        .where(
            Document.workspace_id == workspace_id,
            Document.status.in_(DOCUMENT_CLASSIFIED_OK),
        )
    )
    total = int((await db.execute(count_stmt)).scalar() or 0)

    ids_stmt = (
        select(Document.id)
        .where(
            Document.workspace_id == workspace_id,
            Document.status.in_(DOCUMENT_CLASSIFIED_OK),
        )
        .order_by(Document.uploaded_at.desc())
        .limit(id_limit)
    )
    rows = (await db.execute(ids_stmt)).all()
    ids = [str(r[0]) for r in rows]
    return total, ids


# Stages E2 (extração) — descritivos e legados. Cada artifact_key = 1 documento.
# ``document_id`` é FK opcional não populada pelo pipeline atual; contamos
# artifact_keys distintos como proxy do conjunto de documentos consumidos.
# Público desde A25.l3: lineage_edge_writer reusa para a folha coarse (ADR-279).
EXTRACTION_STAGES: tuple[str, ...] = (
    "extract_statements",
    "extract_invoices",
    "extract_with_llm",
    "E2-extratos",
    "E2-faturas",
    "E2-llm",
)


async def consumed_documents_for_run(
    db: AsyncSession, pipeline_run_id: str | None, *, id_limit: int = 128
) -> tuple[int, list[str]]:
    """DISTINCT ``artifact_key`` em stages E2 da run (proxy de docs extraídos)."""
    if not pipeline_run_id:
        return 0, []
    distinct_key = (
        select(PipelineArtifact.artifact_key)
        .where(
            PipelineArtifact.pipeline_run_id == pipeline_run_id,
            PipelineArtifact.stage.in_(EXTRACTION_STAGES),
        )
        .distinct()
    )
    total = int(
        (await db.execute(select(func.count()).select_from(distinct_key.subquery()))).scalar() or 0
    )
    rows = (await db.execute(distinct_key.limit(id_limit))).all()
    return total, [str(r[0]) for r in rows if r[0] is not None]


def lineage_payload(
    *,
    pipeline_run_id: str | None,
    source_document_count: int,
    source_document_ids: list[str],
    consumed_document_count: int = 0,
    consumed_document_ids: list[str] | None = None,
) -> dict:
    """Metadados incluídos no JSON de análise (GET /reports/{id}/data)."""
    consumed = list(consumed_document_ids or [])
    return {
        "pipeline_run_id": pipeline_run_id,
        "source_document_count": source_document_count,
        "source_document_ids": source_document_ids,
        # CTO-06: ids capados em id_limit (128) → truncamento explícito p/ o consumidor.
        "source_document_ids_truncated": len(source_document_ids) < source_document_count,
        "consumed_document_count": consumed_document_count,
        "consumed_document_ids": consumed,
        "consumed_document_ids_truncated": len(consumed) < consumed_document_count,
    }
