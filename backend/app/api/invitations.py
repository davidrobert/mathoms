"""Invitations router fino — F9 · workspace sharing (A6e.4 · ADR-101 R15/R16).

Rotas **globais** (não tenant-scoped) do fluxo de aceite de convite:

  - `GET  /invitations/{token}`          → preview público (sem auth)
  - `POST /invitations/{token}/accept`   → aceita (exige login)

Gestão (criar/listar/revogar) fica em `api/workspaces.py` sob
`/workspaces/{ws}/invitations/...`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.invitation import (
    accept_invitation as _accept_invitation,
)
from backend.app.application.invitation import (
    preview_invitation as _preview_invitation,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.workspace_members import (
    InvitationAcceptResponse,
    InvitationPreviewResponse,
)

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get(
    "/{token}",
    response_model=InvitationPreviewResponse,
    summary="Preview público do convite — mostra workspace + quem convidou",
)
async def preview_invitation(
    token: str, db: AsyncSession = Depends(get_db)
) -> InvitationPreviewResponse:
    return await _preview_invitation(token, db=db)


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
) -> InvitationAcceptResponse:
    return await _accept_invitation(token, user=user, request=request, db=db)
