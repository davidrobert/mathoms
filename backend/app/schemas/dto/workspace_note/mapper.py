"""Mapper SQLAlchemy ↔ DTO para ``WorkspaceNotes``."""

from __future__ import annotations

from backend.app.models.workspace_note import WorkspaceNotes
from backend.app.schemas.dto.workspace_note.response import WorkspaceNoteResponse


def note_to_response(note: WorkspaceNotes) -> WorkspaceNoteResponse:
    return WorkspaceNoteResponse.model_validate(note)
