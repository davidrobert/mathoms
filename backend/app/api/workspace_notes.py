"""WorkspaceNotes API — router fino (ADR-154, supersede ADR-123 ReportNotes)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.workspace_notes import (
    create_note as _uc_create_note,
)
from backend.app.application.workspace_notes import (
    delete_note as _uc_delete_note,
)
from backend.app.application.workspace_notes import (
    list_notes as _uc_list_notes,
)
from backend.app.application.workspace_notes import (
    update_note as _uc_update_note,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.workspace_notes_repository import (
    WorkspaceNotesRepository,
)
from backend.app.schemas.dto.workspace_note import (
    WorkspaceNoteCreateCommand,
    WorkspaceNoteListResponse,
    WorkspaceNoteResponse,
    WorkspaceNoteUpdateCommand,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/notes", tags=["workspace-notes"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> WorkspaceNotesRepository:
    return WorkspaceNotesRepository(db)


@router.get("", response_model=WorkspaceNoteListResponse)
async def list_notes(
    workspace: Workspace = Depends(get_current_workspace),
    repo: WorkspaceNotesRepository = Depends(_get_repo),
) -> WorkspaceNoteListResponse:
    return await _uc_list_notes(workspace.id, repo=repo)


@router.post(
    "",
    response_model=WorkspaceNoteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def create_note(
    payload: WorkspaceNoteCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: WorkspaceNotesRepository = Depends(_get_repo),
) -> WorkspaceNoteResponse:
    response = await _uc_create_note(
        payload,
        workspace_id=workspace.id,
        author_user_id=user.id,
        repo=repo,
    )
    await db.commit()
    return response


@router.patch(
    "/{note_id}",
    response_model=WorkspaceNoteResponse,
    dependencies=[Depends(require_write_role)],
)
async def update_note(
    note_id: str,
    payload: WorkspaceNoteUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: WorkspaceNotesRepository = Depends(_get_repo),
) -> WorkspaceNoteResponse:
    response = await _uc_update_note(
        payload,
        workspace_id=workspace.id,
        note_id=note_id,
        repo=repo,
    )
    await db.commit()
    return response


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_write_role)],
)
async def delete_note(
    note_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: WorkspaceNotesRepository = Depends(_get_repo),
) -> Response:
    await _uc_delete_note(workspace_id=workspace.id, note_id=note_id, repo=repo)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
