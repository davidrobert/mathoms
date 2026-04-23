"""Invitations API — F9 · workspace sharing.

Contém rotas **independentes de tenant** para o fluxo de aceite de convite:

  - `GET  /invitations/{token}`          → preview (público; sem auth)
  - `POST /invitations/{token}/accept`   → aceita (exige login)

Rotas de gestão (criar/listar/revogar) ficam em `api/workspaces.py` sob
`/workspaces/{ws}/invitations/...`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.workspace_members import (
    InvitationAcceptResponse,
    InvitationPreviewResponse,
)
from backend.app.services import invitation_service
from backend.app.services.audit import client_meta
from backend.app.services.invitation_service import InvitationError

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get(
    "/{token}",
    response_model=InvitationPreviewResponse,
    summary="Preview público do convite — mostra workspace + quem convidou",
)
async def preview_invitation(token: str, db: AsyncSession = Depends(get_db)):
    """Rota PÚBLICA (sem auth). O convidado pode nem ter conta ainda;
    esta rota serve para a landing `/invite/{token}` mostrar o contexto
    antes de pedir login/signup.

    Revela apenas campos do workspace e do inviter — nada sobre outros
    membros ou dados financeiros."""
    inv = await invitation_service.get_by_token(token, db=db)
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado.",
        )

    # tenancy: global — lookup do workspace a partir do invite
    ws_row = await db.execute(select(Workspace).where(Workspace.id == inv.workspace_id))
    workspace = ws_row.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace do convite não existe mais.",
        )

    inviter_name = None
    inviter_email = None
    if inv.invited_by is not None:
        # tenancy: global — inviter é User (não tenant-scoped)
        u_row = await db.execute(select(User).where(User.id == inv.invited_by))
        inviter = u_row.scalar_one_or_none()
        if inviter:
            inviter_name = inviter.full_name
            inviter_email = inviter.email

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


@router.post(
    "/{token}/accept",
    response_model=InvitationAcceptResponse,
    status_code=status.HTTP_200_OK,
    summary="Aceita o convite e cria membership",
)
async def accept_invitation_endpoint(
    token: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exige login. O email do user logado precisa bater com o email
    convidado (case-insensitive)."""
    try:
        member = await invitation_service.accept_invitation(token, acceptor=user, db=db)
    except InvitationError as exc:
        code_to_status = {
            "not_found": status.HTTP_404_NOT_FOUND,
            "expired": status.HTTP_410_GONE,
            "revoked": status.HTTP_410_GONE,
            "already_accepted": status.HTTP_409_CONFLICT,
            "email_mismatch": status.HTTP_403_FORBIDDEN,
        }
        raise HTTPException(
            status_code=code_to_status.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=member.id,
            aggregate_type="workspace_member",
            workspace_id=member.workspace_id,
            action="workspace.member.accept",
            resource_type="workspace_member",
            resource_id=member.id,
            actor_user_id=user.id,
            ip_address=ip,
            user_agent=ua,
            details={"role": member.role},
        ),
        {"db": db},
    )
    await db.commit()
    await db.refresh(member)
    return InvitationAcceptResponse(
        workspace_id=member.workspace_id,
        role=member.role,  # type: ignore[arg-type]
        joined_at=member.joined_at,
    )
