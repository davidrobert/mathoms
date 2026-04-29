"""Use cases do aggregate ``WorkspaceNotes`` (ADR-153)."""

from backend.app.application.workspace_notes.create_note import create_note
from backend.app.application.workspace_notes.delete_note import delete_note
from backend.app.application.workspace_notes.list_notes import list_notes
from backend.app.application.workspace_notes.update_note import update_note

__all__ = [
    "create_note",
    "delete_note",
    "list_notes",
    "update_note",
]
