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


async def consumed_documents_for_run(
    db: AsyncSession, pipeline_run_id: str | None, *, id_limit: int = 128
) -> tuple[int, list[str]]:
    """DISTINCT ``document_id`` em ``pipeline_artifacts`` da run (apenas stages E2 setam essa FK)."""
    if not pipeline_run_id:
        return 0, []
    distinct_doc = (
        select(PipelineArtifact.document_id)
        .where(
            PipelineArtifact.pipeline_run_id == pipeline_run_id,
            PipelineArtifact.document_id.is_not(None),
        )
        .distinct()
    )
    total = int(
        (await db.execute(select(func.count()).select_from(distinct_doc.subquery()))).scalar() or 0
    )
    rows = (await db.execute(distinct_doc.limit(id_limit))).all()
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
    return {
        "pipeline_run_id": pipeline_run_id,
        "source_document_count": source_document_count,
        "source_document_ids": source_document_ids,
        "consumed_document_count": consumed_document_count,
        "consumed_document_ids": list(consumed_document_ids or []),
    }
