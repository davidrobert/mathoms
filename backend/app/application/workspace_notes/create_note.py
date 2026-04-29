"""Use case: cria nova ``WorkspaceNotes`` row."""

from __future__ import annotations

from backend.app.application.workspace_notes._protocols import (
    WorkspaceNotesRepositoryProtocol,
)
from backend.app.models.workspace_note import WorkspaceNotes
from backend.app.schemas.dto.workspace_note import (
    WorkspaceNoteCreateCommand,
    WorkspaceNoteResponse,
    note_to_response,
)


async def create_note(
    cmd: WorkspaceNoteCreateCommand,
    *,
    workspace_id: str,
    author_user_id: str | None,
    repo: WorkspaceNotesRepositoryProtocol,
) -> WorkspaceNoteResponse:
    note = WorkspaceNotes(
        workspace_id=workspace_id,
        title=cmd.title,
        content=cmd.content,
        pinned=cmd.pinned,
        author_user_id=author_user_id,
    )
    added = await repo.add(note)
    return note_to_response(added)
