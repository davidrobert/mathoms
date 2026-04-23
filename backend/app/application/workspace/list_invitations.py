"""Use case: lista convites do workspace (owner-only)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.workspace._dtos import invitation_to_response
from backend.app.schemas.workspace_members import InvitationListResponse
from backend.app.services import invitation_service


async def list_invitations(
    workspace_id: str, *, only_pending: bool, db: AsyncSession
) -> InvitationListResponse:
    invitations = await invitation_service.list_invitations(
        workspace_id, include_terminal=not only_pending, db=db
    )
    return InvitationListResponse(
        invitations=[invitation_to_response(i) for i in invitations],
        total=len(invitations),
    )
