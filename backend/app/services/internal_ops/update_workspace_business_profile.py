"""Atualização do perfil tributário PJ de workspace via console interno (ADR-236 P1)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workspace import Workspace
from backend.app.schemas.business_profile import BusinessProfile
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult


async def _load_workspace(db: AsyncSession, workspace_id: str) -> Workspace | None:
    return (
        await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()


async def get_workspace_business_profile(
    db: AsyncSession,
    workspace_id: str,
) -> OpResult:
    """Retorna o perfil tributário/PJ; default vazio se nunca preenchido."""
    workspace = await _load_workspace(db, workspace_id)
    if workspace is None:
        return OpResult.failure("workspace_not_found", workspace_id=workspace_id)
    return OpResult.success(
        workspace_id=workspace.id,
        profile=dict(workspace.business_profile_json or {}),
    )


def _audit(*, actor: str, ws_id: str, previous: dict, current: dict) -> None:
    append_audit(
        AuditRecord(
            action="workspace.update_business_profile",
            actor=actor,
            target_type="workspace",
            target_id=ws_id,
            details={"previous": previous, "current": current},
        )
    )


async def update_workspace_business_profile(
    db: AsyncSession,
    workspace_id: str,
    *,
    actor: str,
    payload: BusinessProfile,
) -> OpResult:
    """Substitui `Workspace.business_profile_json` (replace, não merge)."""
    workspace = await _load_workspace(db, workspace_id)
    if workspace is None:
        return OpResult.failure("workspace_not_found", workspace_id=workspace_id)

    previous = dict(workspace.business_profile_json or {})
    new_value = payload.model_dump(exclude_none=False)
    workspace.business_profile_json = new_value
    await db.flush()
    _audit(actor=actor, ws_id=workspace.id, previous=previous, current=new_value)
    return OpResult.success(workspace_id=workspace.id, profile=new_value)
