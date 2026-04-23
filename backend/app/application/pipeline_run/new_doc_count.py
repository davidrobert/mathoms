"""Use case: conta documentos nunca processados (``pipeline_last_run_at IS NULL``)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document, DocumentStatus
from backend.app.schemas.pipeline import NewDocCountResponse


async def new_doc_count(workspace_id: str, *, db: AsyncSession) -> NewDocCountResponse:
    result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(
            Document.workspace_id == workspace_id,
            Document.status == DocumentStatus.ready,
            Document.pipeline_last_run_at.is_(None),
        )
    )
    return NewDocCountResponse(new_count=result.scalar() or 0)
