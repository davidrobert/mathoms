"""Use case: lista notas livres do workspace."""

from __future__ import annotations

from backend.app.application.workspace_notes._protocols import (
    WorkspaceNotesRepositoryProtocol,
)
from backend.app.schemas.dto.workspace_note import (
    WorkspaceNoteListResponse,
    note_to_response,
)


async def list_notes(
    workspace_id: str,
    *,
    repo: WorkspaceNotesRepositoryProtocol,
) -> WorkspaceNoteListResponse:
    notes = await repo.list_by_workspace(workspace_id)
    items = [note_to_response(n) for n in notes]
    return WorkspaceNoteListResponse(notes=items, total=len(items))
