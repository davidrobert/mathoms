"""F11.4a — agregado de documentos prontos no workspace (linhagem para relatório)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import DOCUMENT_CLASSIFIED_OK, Document


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


def lineage_payload(
    *,
    pipeline_run_id: str | None,
    source_document_count: int,
    source_document_ids: list[str],
) -> dict:
    """Metadados incluídos no JSON de análise (GET /reports/{id}/data)."""
    return {
        "pipeline_run_id": pipeline_run_id,
        "source_document_count": source_document_count,
        "source_document_ids": source_document_ids,
    }
