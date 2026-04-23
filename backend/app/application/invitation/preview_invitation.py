"""Use case: preview público de convite a partir do token."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.workspace_members import InvitationPreviewResponse
from backend.app.services import invitation_service


async def preview_invitation(
    token: str,
    *,
    db: AsyncSession,
) -> InvitationPreviewResponse:
    inv = await invitation_service.get_by_token(token, db=db)
    if inv is None:
        raise NotFoundError("Convite não encontrado.")

    ws_row = await db.execute(select(Workspace).where(Workspace.id == inv.workspace_id))
    workspace = ws_row.scalar_one_or_none()
    if workspace is None:
        raise NotFoundError("Workspace do convite não existe mais.")

    inviter_name, inviter_email = await _load_inviter(db, inv.invited_by)

    return InvitationPreviewResponse(
        workspace_name=workspace.name,
        workspace_family_surname=workspace.family_surname,
        role=inv.role,  # type: ignore[arg-type]
        invited_by_name=inviter_name,
        invited_by_email=inviter_email,
        email=inv.email,
        expires_at=inv.expires_at,
        status=inv.status(),  # type: ignore[arg-type]
    )


async def _load_inviter(db: AsyncSession, invited_by: str | None) -> tuple[str | None, str | None]:
    if invited_by is None:
        return None, None
    row = await db.execute(select(User).where(User.id == invited_by))
    inviter = row.scalar_one_or_none()
    if inviter is None:
        return None, None
    return inviter.full_name, inviter.email
