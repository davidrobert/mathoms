"""DTOs específicos de /me/workspaces + helpers de serialização."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from backend.app.models.workspace_invitation import WorkspaceInvitation
from backend.app.schemas.workspace_members import InvitationResponse


class UserWorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    family_surname: str | None = None
    role: Literal["owner", "member", "viewer"]
    joined_at: datetime


class UserWorkspaceListResponse(BaseModel):
    workspaces: list[UserWorkspaceResponse]
    total: int


def invitation_to_response(inv: WorkspaceInvitation) -> InvitationResponse:
    return InvitationResponse(
        id=inv.id,
        workspace_id=inv.workspace_id,
        email=inv.email,
        role=inv.role,  # type: ignore[arg-type]
        status=inv.status(),  # type: ignore[arg-type]
        invited_by=inv.invited_by,
        expires_at=inv.expires_at,
        accepted_at=inv.accepted_at,
        revoked_at=inv.revoked_at,
        created_at=inv.created_at,
    )
