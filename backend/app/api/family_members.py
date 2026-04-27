"""Family Members API — router fino (A6e.3 · ADR-101 R15/R16).

Endpoints sob ``/workspaces/{workspace_id}/config/members[/accounts]``
delegam a use cases em :mod:`backend.app.application.family_member`.
Erros de domínio são traduzidos para HTTP por handlers globais em
``main.py`` (NotFoundError → 404, ConflictError → 409).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.family_member import (
    create_bank_account,
    create_family_member,
    delete_bank_account,
    delete_family_member,
    list_bank_accounts,
    list_family_members,
    update_bank_account,
    update_family_member,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.family_member_repository import FamilyMemberRepository
from backend.app.schemas.dto.family_member import (
    BankAccountCreateCommand,
    BankAccountResponse,
    BankAccountUpdateCommand,
    FamilyMemberCreateCommand,
    FamilyMemberListResponse,
    FamilyMemberResponse,
    FamilyMemberUpdateCommand,
)
from backend.app.services.vault import get_vault

router = APIRouter(prefix="/workspaces/{workspace_id}/config", tags=["config"])
_vault = get_vault()


def _get_repo(db: AsyncSession = Depends(get_db)) -> FamilyMemberRepository:
    return FamilyMemberRepository(db)


@router.get("/members", response_model=FamilyMemberListResponse)
async def list_members(
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
) -> FamilyMemberListResponse:
    # A8.0: `config/family_members.json` deletado em A7.5; workspace sem rows
    # retorna lista vazia (comportamento correto multi-tenant — não vaza
    # identidade do founder, F6.5E.6).
    return await list_family_members(workspace.id, repo=repo, vault=_vault)


@router.post(
    "/members",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_member(
    body: FamilyMemberCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyMemberResponse:
    return await create_family_member(
        body,
        workspace_id=workspace.id,
        repo=repo,
        vault=_vault,
        db=db,
        actor_user_id=current_user.id,
    )


@router.put("/members/{member_id}", response_model=FamilyMemberResponse)
async def update_member(
    member_id: str,
    body: FamilyMemberUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
) -> FamilyMemberResponse:
    return await update_family_member(
        member_id, body, workspace_id=workspace.id, repo=repo, vault=_vault
    )


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
) -> None:
    await delete_family_member(member_id, workspace_id=workspace.id, repo=repo)


@router.get("/members/{member_id}/accounts", response_model=list[BankAccountResponse])
async def list_accounts(
    member_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
) -> list[BankAccountResponse]:
    return await list_bank_accounts(member_id, workspace_id=workspace.id, repo=repo)


@router.post(
    "/members/{member_id}/accounts",
    response_model=BankAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    member_id: str,
    body: BankAccountCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
) -> BankAccountResponse:
    return await create_bank_account(member_id, body, workspace_id=workspace.id, repo=repo)


@router.put("/members/{member_id}/accounts/{account_id}", response_model=BankAccountResponse)
async def update_account(
    member_id: str,
    account_id: str,
    body: BankAccountUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
) -> BankAccountResponse:
    return await update_bank_account(
        member_id, account_id, body, workspace_id=workspace.id, repo=repo
    )


@router.delete(
    "/members/{member_id}/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_account(
    member_id: str,
    account_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
) -> None:
    await delete_bank_account(member_id, account_id, workspace_id=workspace.id, repo=repo)
