"""Exclusão individual de documento (7F.17 · ADR-116).

Remove linha do `documents` + blob em disco (se `stored_path` existir).
Audit grava nome do arquivo + hash para rastreabilidade.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.document import Document
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult


def _resolve_blob_path(stored_path: str | None, workspace_id: str) -> Path | None:
    if not stored_path:
        return None
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return Path(settings.STORAGE_ROOT) / workspace_id / stored_path


async def delete_document(
    db: AsyncSession, document_id: str, *, actor: str
) -> OpResult:
    doc = (
        await db.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if doc is None:
        return OpResult.failure("document_not_found", document_id=document_id)

    blob = _resolve_blob_path(doc.stored_path, doc.workspace_id)
    blob_removed = False
    if blob is not None and blob.exists():
        blob.unlink()
        blob_removed = True

    details = {
        "original_name": doc.original_name,
        "content_hash": doc.content_hash,
        "workspace_id": doc.workspace_id,
        "blob_removed": blob_removed,
    }

    await db.delete(doc)
    await db.flush()

    append_audit(
        AuditRecord(
            action="document.delete",
            actor=actor,
            target_type="document",
            target_id=document_id,
            details=details,
        )
    )
    return OpResult.success(document_id=document_id, **details)
