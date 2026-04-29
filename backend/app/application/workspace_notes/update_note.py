"""Use case: atualiza ``WorkspaceNotes`` (PATCH semantics)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.workspace_notes._protocols import (
    WorkspaceNotesRepositoryProtocol,
)
from backend.app.schemas.dto.workspace_note import (
    WorkspaceNoteResponse,
    WorkspaceNoteUpdateCommand,
    note_to_response,
)


async def update_note(
    cmd: WorkspaceNoteUpdateCommand,
    *,
    workspace_id: str,
    note_id: str,
    repo: WorkspaceNotesRepositoryProtocol,
) -> WorkspaceNoteResponse:
    note = await repo.get_by_id(workspace_id, note_id)
    if note is None:
        raise NotFoundError(f"WorkspaceNote {note_id} não encontrada", code="note_not_found")
    if cmd.title is not None:
        note.title = cmd.title
    if cmd.content is not None:
        note.content = cmd.content
    if cmd.pinned is not None:
        note.pinned = cmd.pinned
    return note_to_response(note)
