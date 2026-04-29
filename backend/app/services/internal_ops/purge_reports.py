"""Purge bulk de relatórios + artefato E5 referenciado (ADR-116)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.report import Report
from backend.app.models.report_collab import KanbanItem, ReportNotes
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult
from backend.app.services.internal_ops.scope import (
    PurgeScope,
    resolve_scope_context,
    resolve_workspace_ids,
)

__all__ = ["purge_reports"]


async def _target_reports(db: AsyncSession, ws_ids: list[str]) -> list[Report]:
    if not ws_ids:
        return []
    stmt = select(Report).where(Report.workspace_id.in_(ws_ids))
    return list((await db.execute(stmt)).scalars().all())


async def _delete_report_collab(db: AsyncSession, report_ids: list[str]) -> None:
    if not report_ids:
        return
    await db.execute(delete(ReportNotes).where(ReportNotes.report_id.in_(report_ids)))
    await db.execute(delete(KanbanItem).where(KanbanItem.report_id.in_(report_ids)))


async def _delete_artifacts(db: AsyncSession, artifact_ids: list[int]) -> int:
    if not artifact_ids:
        return 0
    result = await db.execute(delete(PipelineArtifact).where(PipelineArtifact.id.in_(artifact_ids)))
    return result.rowcount or 0


def _build_summary(
    reports: list[Report], artifact_ids: list[int], scope: PurgeScope, context_dict: dict
) -> dict:
    return {
        "count": len(reports),
        "ids": [r.id for r in reports],
        "artifacts_to_remove": len(artifact_ids),
        "scope": {"user_id": scope.user_id, "workspace_id": scope.workspace_id},
        "scope_context": context_dict,
    }


def _audit_purge(actor: str, scope: PurgeScope, summary: dict, artifacts_removed: int) -> None:
    append_audit(
        AuditRecord(
            action="report.purge",
            actor=actor,
            target_type="reports",
            target_id=scope.workspace_id or scope.user_id,
            details={
                "count": summary["count"],
                "artifacts_removed": artifacts_removed,
                "scope": summary["scope"],
            },
        )
    )


async def _execute_purge(db: AsyncSession, reports: list[Report], artifact_ids: list[int]) -> int:
    report_ids = [r.id for r in reports]
    await _delete_report_collab(db, report_ids)
    if report_ids:
        await db.execute(delete(Report).where(Report.id.in_(report_ids)))
    artifacts_removed = await _delete_artifacts(db, artifact_ids)
    await db.flush()
    return artifacts_removed


async def _collect(db: AsyncSession, scope: PurgeScope) -> tuple[list[Report], list[int], dict]:
    ws_ids = await resolve_workspace_ids(db, scope)
    reports = await _target_reports(db, ws_ids)
    artifact_ids = [r.analysis_artifact_id for r in reports if r.analysis_artifact_id is not None]
    ctx = await resolve_scope_context(db, scope)
    summary = _build_summary(
        reports,
        artifact_ids,
        scope,
        {"owner_email": ctx.owner_email, "workspace_names": list(ctx.workspace_names)},
    )
    return reports, artifact_ids, summary


async def purge_reports(
    db: AsyncSession,
    *,
    scope: PurgeScope,
    actor: str,
    preview: bool = True,
) -> OpResult:
    if not scope.user_id and not scope.workspace_id:
        return OpResult.failure("scope_required")
    reports, artifact_ids, summary = await _collect(db, scope)
    if preview:
        return OpResult.success(preview=True, **summary)
    artifacts_removed = await _execute_purge(db, reports, artifact_ids)
    _audit_purge(actor, scope, summary, artifacts_removed)
    return OpResult.success(preview=False, artifacts_removed=artifacts_removed, **summary)
