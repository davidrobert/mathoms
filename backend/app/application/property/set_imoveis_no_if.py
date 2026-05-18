"""Use case: seta `workspaces.imoveis_no_if` per-workspace (ADR-222)."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.repositories.property_repository import PropertyRepository
from backend.app.schemas.dto.property import ImoveisNoIfCommand, ImoveisNoIfResponse


async def set_imoveis_no_if(
    workspace_id: str, cmd: ImoveisNoIfCommand, *, repo: PropertyRepository, user_id: str
) -> ImoveisNoIfResponse:
    """Flippa toggle + popula audit (`set_at`, `set_by_user_id`)."""
    workspace = await repo.get_workspace(workspace_id)
    if workspace is None:
        raise LookupError(f"workspace {workspace_id} não encontrado")
    now = datetime.now(timezone.utc)
    workspace.imoveis_no_if = cmd.imoveis_no_if
    workspace.imoveis_no_if_set_at = now
    workspace.imoveis_no_if_set_by_user_id = user_id
    await repo._db.commit()  # type: ignore[attr-defined]
    return ImoveisNoIfResponse(
        workspace_id=workspace_id,
        imoveis_no_if=cmd.imoveis_no_if,
        set_at=now,
        set_by_user_id=user_id,
    )
