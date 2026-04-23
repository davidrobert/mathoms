"""Workspaces router fino — /me/workspaces + members + invitations (A6e.4 · ADR-101 R15/R16).

Contém dois routers:

  - ``router``         → ``/me/workspaces`` — me-centric (lista memberships do
                        user logado).
  - ``tenant_router``  → ``/workspaces/{workspace_id}/{members,invitations}`` —
                        tenant-scoped, usa ``get_current_workspace`` e
                        ``require_member_admin_role``.

Rotas públicas de aceite de convite vivem em ``api/invitations.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.workspace import (
    create_invitation as _create_invitation,
)
from backend.app.application.workspace import (
    list_invitations as _list_invitations,
)
from backend.app.application.workspace import (
    list_members as _list_members,
)
from backend.app.application.workspace import (
    list_my_workspaces as _list_my_workspaces,
)
from backend.app.application.workspace import (
    remove_member as _remove_member,
)
from backend.app.application.workspace import (
    revoke_invitation as _revoke_invitation,
)
from backend.app.application.workspace import (
    update_member_role as _update_member_role,
)
from backend.app.application.workspace._dtos import (
    UserWorkspaceListResponse,
    UserWorkspaceResponse,  # noqa: F401  # re-export de tipo público (test/import histórico)
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_member_admin_role
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.workspace_members import (
    InvitationCreateRequest,
    InvitationCreateResponse,
    InvitationListResponse,
    MemberListResponse,
    MemberResponse,
    MemberRoleUpdateRequest,
)

# ─── /me/workspaces (me-centric) ────────────────────────────────────

router = APIRouter(prefix="/me", tags=["workspaces"])


@router.get("/workspaces", response_model=UserWorkspaceListResponse)
async def list_my_workspaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWorkspaceListResponse:
    return await _list_my_workspaces(user.id, db=db)


# ─── /workspaces/{ws}/members + invitations (tenant-scoped) ────────

tenant_router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["workspaces"],
)


@tenant_router.get("/members", response_model=MemberListResponse)
async def list_members_endpoint(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> MemberListResponse:
    return await _list_members(workspace.id, db=db)


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
) -> MemberResponse:
    return await _update_member_role(
        workspace.id, user_id, body, actor=actor, request=request, db=db
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
) -> None:
    await _remove_member(workspace.id, user_id, actor=actor, request=request, db=db)


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
) -> InvitationCreateResponse:
    return await _create_invitation(workspace.id, body, actor=actor, request=request, db=db)


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
) -> InvitationListResponse:
    return await _list_invitations(workspace.id, only_pending=only_pending, db=db)


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
) -> None:
    await _revoke_invitation(workspace.id, invitation_id, actor=actor, request=request, db=db)
