"""Family Members API — router fino (A6e.3 · ADR-101 R15/R16).

Endpoints sob ``/workspaces/{workspace_id}/config/members[/accounts]``
delegam a use cases em :mod:`backend.app.application.family_member`.
Erros de domínio são traduzidos para HTTP por handlers globais em
``main.py`` (NotFoundError → 404, ConflictError → 409).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.family_member import (
    create_bank_account,
    create_family_member,
    delete_bank_account,
    delete_family_member,
    dismiss_irpf_suggestion,
    get_irpf_suggestions,
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
    IrpfDismissCommand,
    SuggestionsFromIrpfResponse,
)
from backend.app.services.access_audit import record_access_audit
from backend.app.services.audit import AuditAction
from backend.app.services.irpf_suggestion_adapters import (
    DBInstitutionLabelResolver,
    DBIrpfArtifactSource,
    find_dismissal_for_account,
    normalize_account_digits,
)
from backend.app.services.vault import get_vault

router = APIRouter(prefix="/workspaces/{workspace_id}/config", tags=["config"])
_vault = get_vault()
_irpf_telemetry = logging.getLogger("mathoms.irpf_suggestions")


def _get_repo(db: AsyncSession = Depends(get_db)) -> FamilyMemberRepository:
    return FamilyMemberRepository(db)


@router.get(
    "/members",
    response_model=FamilyMemberListResponse,
    dependencies=[Depends(record_access_audit(AuditAction.family_member_read, "family_member"))],
)
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


@router.get(
    "/members/{member_id}/accounts",
    response_model=list[BankAccountResponse],
    dependencies=[
        Depends(
            record_access_audit(
                AuditAction.family_member_read, "bank_account", resource_id_param="member_id"
            )
        )
    ],
)
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
    db: AsyncSession = Depends(get_db),
) -> BankAccountResponse:
    response = await create_bank_account(member_id, body, workspace_id=workspace.id, repo=repo)
    if body.origem_irpf:
        await _emit_irpf_accepted_telemetry(db, workspace_id=workspace.id, body=body)
    return response


def _log_irpf_event(event: str, *, workspace_id: str, irpf_year: int, institution: str) -> None:
    _irpf_telemetry.info(
        "%s workspace=%s irpf_year=%d institution=%s",
        event,
        workspace_id,
        irpf_year,
        institution,
    )


async def _has_prior_dismissal(
    db: AsyncSession, *, workspace_id: str, institution: str, account_number: Optional[str]
) -> bool:
    norm = normalize_account_digits(account_number)
    if not norm:
        return False
    found = await find_dismissal_for_account(
        db, workspace_id=workspace_id, institution_code=institution, account_number_norm=norm
    )
    return found is not None


async def _emit_irpf_accepted_telemetry(
    db: AsyncSession, *, workspace_id: str, body: BankAccountCreateCommand
) -> None:
    year = body.origem_irpf_year or 0
    inst = body.institution_code
    _log_irpf_event("accepted", workspace_id=workspace_id, irpf_year=year, institution=inst)
    if await _has_prior_dismissal(
        db, workspace_id=workspace_id, institution=inst, account_number=body.account_number
    ):
        _log_irpf_event(
            "dismissed_then_re_added", workspace_id=workspace_id, irpf_year=year, institution=inst
        )


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


# ---------------------------------------------------------------------------
# ADR-229: IRPF pre-fill — suggestions + dismissals
# ---------------------------------------------------------------------------


@router.get(
    "/members/suggestions-from-irpf",
    response_model=SuggestionsFromIrpfResponse,
    dependencies=[Depends(record_access_audit(AuditAction.family_member_read, "irpf_suggestion"))],
)
async def list_suggestions_from_irpf(
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_db),
) -> SuggestionsFromIrpfResponse:
    response = await get_irpf_suggestions(
        workspace_id=workspace.id,
        repo=repo,
        irpf_source=DBIrpfArtifactSource(db),
        institution_labels=DBInstitutionLabelResolver(db),
    )
    _irpf_telemetry.info(
        "shown workspace=%s irpf_year=%d count=%d filtered_exact=%d dismissed=%d",
        workspace.id,
        response.irpf_year,
        len(response.suggestions),
        response.total_filtered_exact_match,
        response.total_dismissed,
    )
    return response


@router.post(
    "/members/irpf-dismissals",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def dismiss_suggestion(
    body: IrpfDismissCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: FamilyMemberRepository = Depends(_get_repo),
    current_user: User = Depends(get_current_user),
) -> None:
    await dismiss_irpf_suggestion(
        body, workspace_id=workspace.id, repo=repo, actor_user_id=current_user.id
    )
    _log_irpf_event(
        "dismissed",
        workspace_id=workspace.id,
        irpf_year=body.irpf_year,
        institution=body.institution_code,
    )
