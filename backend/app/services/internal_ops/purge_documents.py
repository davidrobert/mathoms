"""Purge bulk de documentos por escopo (7F.12 · ADR-116).

Dois modos:
- `preview=True`  → retorna contagem + lista de ids; não muta.
- `preview=False` → deleta rows + blobs; audit registra totais.

Escopo via `user_id` (todos os workspaces do user) **ou** `workspace_id`.
Pelo menos um deve vir.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.workspace import Workspace
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.delete_document import _resolve_blob_path
from backend.app.services.internal_ops.results import OpResult


@dataclass(frozen=True)
class PurgeScope:
    user_id: str | None = None
    workspace_id: str | None = None


async def _target_documents(db: AsyncSession, scope: PurgeScope) -> list[Document]:
    if scope.workspace_id:
        stmt = select(Document).where(Document.workspace_id == scope.workspace_id)
    elif scope.user_id:
        ws_ids_rows = await db.execute(
            select(Workspace.id).where(Workspace.owner_id == scope.user_id)
        )
        ws_ids = [r[0] for r in ws_ids_rows.all()]
        if not ws_ids:
            return []
        stmt = select(Document).where(Document.workspace_id.in_(ws_ids))
    else:
        return []
    return list((await db.execute(stmt)).scalars().all())


async def purge_documents(
    db: AsyncSession,
    *,
    scope: PurgeScope,
    actor: str,
    preview: bool = True,
) -> OpResult:
    if not scope.user_id and not scope.workspace_id:
        return OpResult.failure("scope_required")

    docs = await _target_documents(db, scope)
    summary = {
        "count": len(docs),
        "ids": [d.id for d in docs],
        "scope": {"user_id": scope.user_id, "workspace_id": scope.workspace_id},
    }
    if preview:
        return OpResult.success(preview=True, **summary)

    blobs_removed = 0
    for doc in docs:
        blob = _resolve_blob_path(doc.stored_path, doc.workspace_id)
        if blob is not None and blob.exists():
            blob.unlink()
            blobs_removed += 1
        await db.delete(doc)
    await db.flush()

    append_audit(
        AuditRecord(
            action="document.purge",
            actor=actor,
            target_type="documents",
            target_id=scope.workspace_id or scope.user_id,
            details={
                "count": summary["count"],
                "blobs_removed": blobs_removed,
                "scope": summary["scope"],
            },
        )
    )
    return OpResult.success(preview=False, blobs_removed=blobs_removed, **summary)
