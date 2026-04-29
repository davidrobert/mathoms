"""Use case: remove ``WorkspaceNotes`` row do workspace."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.workspace_notes._protocols import (
    WorkspaceNotesRepositoryProtocol,
)


async def delete_note(
    *,
    workspace_id: str,
    note_id: str,
    repo: WorkspaceNotesRepositoryProtocol,
) -> None:
    note = await repo.get_by_id(workspace_id, note_id)
    if note is None:
        raise NotFoundError(
            f"WorkspaceNote {note_id} não encontrada no workspace",
            code="note_not_found",
        )
    await repo.delete(note)
