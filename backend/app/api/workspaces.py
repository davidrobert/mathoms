"""Workspaces API — F8 (list memberships) + F9 (members & invitations).

Contém dois routers:

  - `router`         → `/me/workspaces` — me-centric (lista memberships do
                         user logado).
  - `tenant_router`  → `/workspaces/{workspace_id}/{members,invitations}` —
                         tenant-scoped, usa `get_current_workspace` e
                         `require_member_admin_role`.

Rotas públicas de aceite de convite vivem em `api/invitations.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import (
    get_current_workspace,
    require_member_admin_role,
)
from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.workspace_member import WorkspaceMember
from backend.app.schemas.workspace_members import (
    InvitationCreateRequest,
    InvitationCreateResponse,
    InvitationListResponse,
    InvitationResponse,
    MemberListResponse,
    MemberResponse,
    MemberRoleUpdateRequest,
)
from backend.app.services import (
    invitation_service,
    membership_service,
)
from backend.app.services.audit import client_meta
from backend.app.services.invitation_service import InvitationError
from backend.app.services.membership_service import MembershipError

# ─── /me/workspaces (me-centric) ────────────────────────────────────

router = APIRouter(prefix="/me", tags=["workspaces"])


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


@router.get("/workspaces", response_model=UserWorkspaceListResponse)
async def list_my_workspaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista memberships do usuário. Ordenado por joined_at (mais antigo
    primeiro — workspace "primário" fica em primeiro lugar)."""
    # tenancy: global — auth-level listing of user's memberships
    stmt = (
        select(WorkspaceMember, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(WorkspaceMember.joined_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    items = [
        UserWorkspaceResponse(
            id=ws.id,
            name=ws.name,
            family_surname=ws.family_surname,
            role=wm.role,  # type: ignore[arg-type]
            joined_at=wm.joined_at,
        )
        for wm, ws in rows
    ]
    return UserWorkspaceListResponse(workspaces=items, total=len(items))


# ─── /workspaces/{ws}/members (tenant-scoped) ──────────────────────

tenant_router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["workspaces"],
)


def _invitation_to_response(inv) -> InvitationResponse:
    return InvitationResponse(
        id=inv.id,
        workspace_id=inv.workspace_id,
        email=inv.email,
        role=inv.role,
        status=inv.status(),
        invited_by=inv.invited_by,
        expires_at=inv.expires_at,
        accepted_at=inv.accepted_at,
        revoked_at=inv.revoked_at,
        created_at=inv.created_at,
    )


@tenant_router.get("/members", response_model=MemberListResponse)
async def list_members_endpoint(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Lista membros do workspace. Qualquer membro (incluindo viewer) pode
    ver — saber quem mais tem acesso é informação básica de confiança."""
    rows = await membership_service.list_members(workspace.id, db=db)
    return MemberListResponse(
        members=[
            MemberResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=m.role,  # type: ignore[arg-type]
                joined_at=m.joined_at,
                invited_by=m.invited_by,
            )
            for m, user in rows
        ],
        total=len(rows),
    )


@tenant_router.patch(
    "/members/{user_id}",
    response_model=MemberResponse,
    dependencies=[Depends(require_member_admin_role)],
)
async def update_member_role_endpoint(
    user_id: str,
    body: MemberRoleUpdateRequest,
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Muda o role de um membro. Owner-only. Não pode mudar o role de um
    owner (use transferência de ownership — não disponível ainda)."""
    member = await membership_service.get_member(workspace.id, user_id, db=db)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro não encontrado.",
        )
    previous_role = member.role

    try:
        updated = await membership_service.update_member_role(
            workspace.id, user_id, new_role=body.role, db=db
        )
    except MembershipError as exc:
        code_to_status = {
            "not_found": status.HTTP_404_NOT_FOUND,
            "is_owner": status.HTTP_409_CONFLICT,
            "invalid_role": status.HTTP_422_UNPROCESSABLE_ENTITY,
        }
        raise HTTPException(
            status_code=code_to_status.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=updated.id,
            aggregate_type="workspace_member",
            workspace_id=workspace.id,
            action="workspace.member.role_change",
            resource_type="workspace_member",
            resource_id=updated.id,
            actor_user_id=actor.id,
            ip_address=ip,
            user_agent=ua,
            details={
                "target_user_id": user_id,
                "from_role": previous_role,
                "to_role": updated.role,
            },
        ),
        {"db": db},
    )
    await db.commit()
    await db.refresh(updated)

    # tenancy: global — re-fetch do user para formar MemberResponse completo
    u_row = await db.execute(select(User).where(User.id == user_id))
    user_obj = u_row.scalar_one()
    return MemberResponse(
        user_id=user_obj.id,
        email=user_obj.email,
        full_name=user_obj.full_name,
        role=updated.role,  # type: ignore[arg-type]
        joined_at=updated.joined_at,
        invited_by=updated.invited_by,
    )


@tenant_router.delete(
    "/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_member_admin_role)],
)
async def remove_member_endpoint(
    user_id: str,
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove um membro. Owner-only. Não permite remover o próprio owner."""
    try:
        removed = await membership_service.remove_member(workspace.id, user_id, db=db)
    except MembershipError as exc:
        code_to_status = {
            "not_found": status.HTTP_404_NOT_FOUND,
            "is_owner": status.HTTP_409_CONFLICT,
        }
        raise HTTPException(
            status_code=code_to_status.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=removed.id,
            aggregate_type="workspace_member",
            workspace_id=workspace.id,
            action="workspace.member.remove",
            resource_type="workspace_member",
            resource_id=removed.id,
            actor_user_id=actor.id,
            ip_address=ip,
            user_agent=ua,
            details={"target_user_id": user_id, "role": removed.role},
        ),
        {"db": db},
    )
    await db.commit()


# ─── /workspaces/{ws}/invitations (tenant-scoped) ──────────────────


@tenant_router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_member_admin_role)],
)
async def create_invitation_endpoint(
    body: InvitationCreateRequest,
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria um convite. Owner-only.

    Retorna o **token cru** na resposta — esse é o único momento em que
    ele fica visível. Inclua em `/invite/{token}` e envie o link ao
    convidado (WhatsApp, SMS, pessoalmente). F9.8 ligará envio por
    email."""
    try:
        invitation, raw_token = await invitation_service.create_invitation(
            workspace.id,
            email=body.email,
            role=body.role,
            invited_by=actor.id,
            db=db,
        )
    except InvitationError as exc:
        code_to_status = {
            "invalid_role": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "already_member": status.HTTP_409_CONFLICT,
            "limit_reached": status.HTTP_429_TOO_MANY_REQUESTS,
        }
        raise HTTPException(
            status_code=code_to_status.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=invitation.id,
            aggregate_type="workspace_invitation",
            workspace_id=workspace.id,
            action="workspace.member.invite",
            resource_type="workspace_invitation",
            resource_id=invitation.id,
            actor_user_id=actor.id,
            ip_address=ip,
            user_agent=ua,
            details={"email": body.email, "role": body.role},
        ),
        {"db": db},
    )
    await db.commit()
    await db.refresh(invitation)
    return InvitationCreateResponse(
        invitation=_invitation_to_response(invitation),
        token=raw_token,
        invite_path=f"/invite/{raw_token}",
    )


@tenant_router.get(
    "/invitations",
    response_model=InvitationListResponse,
    dependencies=[Depends(require_member_admin_role)],
)
async def list_invitations_endpoint(
    only_pending: bool = Query(
        False, description="Se true, lista apenas convites em estado pending."
    ),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Lista convites do workspace. Owner-only (só quem convida precisa
    ver convites em andamento)."""
    invitations = await invitation_service.list_invitations(
        workspace.id, include_terminal=not only_pending, db=db
    )
    return InvitationListResponse(
        invitations=[_invitation_to_response(i) for i in invitations],
        total=len(invitations),
    )


@tenant_router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_member_admin_role)],
)
async def revoke_invitation_endpoint(
    invitation_id: str,
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoga um convite pendente. Owner-only. Idempotente."""
    try:
        inv = await invitation_service.revoke_invitation(workspace.id, invitation_id, db=db)
    except InvitationError as exc:
        code_to_status = {
            "not_found": status.HTTP_404_NOT_FOUND,
            "already_accepted": status.HTTP_409_CONFLICT,
        }
        raise HTTPException(
            status_code=code_to_status.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=inv.id,
            aggregate_type="workspace_invitation",
            workspace_id=workspace.id,
            action="workspace.member.revoke_invite",
            resource_type="workspace_invitation",
            resource_id=inv.id,
            actor_user_id=actor.id,
            ip_address=ip,
            user_agent=ua,
            details={"email": inv.email},
        ),
        {"db": db},
    )
    await db.commit()
