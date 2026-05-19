"""Use case: atualizar conta bancária (PUT com replace completo)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)
from backend.app.schemas.dto.family_member import (
    BankAccountResponse,
    BankAccountUpdateCommand,
)


async def update_bank_account(
    member_id: str,
    account_id: str,
    cmd: BankAccountUpdateCommand,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
) -> BankAccountResponse:
    """Garante membro+conta existem no workspace antes do update."""
    member = await repo.get_by_id(workspace_id, member_id)
    if not member:
        raise NotFoundError("Membro não encontrado", code="member_not_found")
    account = await repo.get_account(member_id, account_id)
    if not account:
        raise NotFoundError("Conta bancária não encontrada", code="account_not_found")
    updated = await repo.update_account(
        account,
        institution_code=cmd.institution_code,
        account_type=cmd.account_type,
        agency=cmd.agency,
        account_number=cmd.account_number,
        label=cmd.label,
        is_joint=cmd.is_joint,
        co_titulares=cmd.co_titulares,
    )
    return BankAccountResponse.model_validate(updated)
