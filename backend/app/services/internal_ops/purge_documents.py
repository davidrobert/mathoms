"""Purge bulk de documentos por escopo (7F.12 · ADR-116)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineStageLog
from backend.app.models.stage_review import StageReview
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.delete_document import _resolve_blob_path
from backend.app.services.internal_ops.results import OpResult
from backend.app.services.internal_ops.scope import (
    PurgeScope,
    resolve_scope_context,
    resolve_workspace_ids,
)

__all__ = ["PurgeScope", "purge_documents"]


async def _target_documents(db: AsyncSession, ws_ids: list[str]) -> list[Document]:
    if not ws_ids:
        return []
    stmt = select(Document).where(Document.workspace_id.in_(ws_ids))
    return list((await db.execute(stmt)).scalars().all())


async def _target_run_ids(db: AsyncSession, ws_ids: list[str]) -> list[str]:
    if not ws_ids:
        return []
    stmt = select(PipelineRun.id).where(PipelineRun.workspace_id.in_(ws_ids))
    return [r[0] for r in (await db.execute(stmt)).all()]


def _unlink_blobs(docs: list[Document]) -> tuple[int, list[str]]:
    blobs_removed = 0
    failed: list[str] = []
    for doc in docs:
        blob = _resolve_blob_path(doc.stored_path, doc.workspace_id)
        if blob is None or not blob.exists():
            continue
        try:
            blob.unlink()
            blobs_removed += 1
        except OSError:
            failed.append(doc.id)
    return blobs_removed, failed


async def _delete_pipeline_data(db: AsyncSession, ws_ids: list[str], run_ids: list[str]) -> None:
    """DELETEs explícitos — não dependemos de PRAGMA foreign_keys do SQLite."""
    if ws_ids:
        await db.execute(delete(PipelineArtifact).where(PipelineArtifact.workspace_id.in_(ws_ids)))
    if run_ids:
        await db.execute(
            delete(PipelineStageLog).where(PipelineStageLog.pipeline_run_id.in_(run_ids))
        )
        await db.execute(delete(StageReview).where(StageReview.pipeline_run_id.in_(run_ids)))
        await db.execute(delete(PipelineRun).where(PipelineRun.id.in_(run_ids)))


def _build_summary(
    docs: list[Document], run_ids: list[str], scope: PurgeScope, context_dict: dict
) -> dict:
    return {
        "count": len(docs),
        "ids": [d.id for d in docs],
        "items": [{"id": d.id, "name": d.original_name} for d in docs],
        "runs_to_remove": len(run_ids),
        "scope": {"user_id": scope.user_id, "workspace_id": scope.workspace_id},
        "scope_context": context_dict,
    }


def _audit_purge(actor: str, scope: PurgeScope, details: dict, result: str = "ok") -> None:
    append_audit(
        AuditRecord(
            action="document.purge",
            actor=actor,
            target_type="documents",
            target_id=scope.workspace_id or scope.user_id,
            result=result,
            details=details,
        )
    )


def _partial_failure_result(
    actor: str, scope: PurgeScope, summary: dict, blobs_removed: int, failed_blobs: list[str]
) -> OpResult:
    details = {
        "count": summary["count"],
        "blobs_removed": blobs_removed,
        "failed_blobs": failed_blobs,
        "scope": summary["scope"],
    }
    _audit_purge(actor, scope, details, result="partial_failure")
    return OpResult.failure(
        "partial_failure",
        preview=False,
        count=summary["count"],
        ids=summary["ids"],
        failed_blobs=failed_blobs,
        blobs_removed=blobs_removed,
    )


async def _do_purge(db: AsyncSession, ws_ids: list[str], run_ids: list[str]) -> None:
    await _delete_pipeline_data(db, ws_ids, run_ids)
    if ws_ids:
        await db.execute(delete(Document).where(Document.workspace_id.in_(ws_ids)))
    await db.flush()


async def _collect(
    db: AsyncSession, scope: PurgeScope
) -> tuple[list[Document], list[str], list[str], dict]:
    ws_ids = await resolve_workspace_ids(db, scope)
    docs = await _target_documents(db, ws_ids)
    run_ids = await _target_run_ids(db, ws_ids)
    ctx = await resolve_scope_context(db, scope)
    summary = _build_summary(
        docs,
        run_ids,
        scope,
        {"owner_email": ctx.owner_email, "workspace_names": list(ctx.workspace_names)},
    )
    return docs, ws_ids, run_ids, summary


async def purge_documents(
    db: AsyncSession,
    *,
    scope: PurgeScope,
    actor: str,
    preview: bool = True,
) -> OpResult:
    if not scope.user_id and not scope.workspace_id:
        return OpResult.failure("scope_required")
    docs, ws_ids, run_ids, summary = await _collect(db, scope)
    if preview:
        return OpResult.success(preview=True, **summary)
    blobs_removed, failed = _unlink_blobs(docs)
    if failed:
        await db.rollback()
        return _partial_failure_result(actor, scope, summary, blobs_removed, failed)
    await _do_purge(db, ws_ids, run_ids)
    _audit_purge(
        actor,
        scope,
        {
            "count": summary["count"],
            "blobs_removed": blobs_removed,
            "runs_removed": len(run_ids),
            "scope": summary["scope"],
        },
    )
    return OpResult.success(
        preview=False, blobs_removed=blobs_removed, runs_removed=len(run_ids), **summary
    )
