"""Use case: criar conta bancária vinculada a um membro."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)
from backend.app.schemas.dto.family_member import (
    BankAccountCreateCommand,
    BankAccountResponse,
)


async def create_bank_account(
    member_id: str,
    cmd: BankAccountCreateCommand,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
) -> BankAccountResponse:
    """Valida membership e adiciona a conta."""
    member = await repo.get_by_id(workspace_id, member_id)
    if not member:
        raise NotFoundError("Membro não encontrado", code="member_not_found")
    account = await repo.add_account(
        member_id,
        institution_code=cmd.institution_code,
        account_type=cmd.account_type,
        agency=cmd.agency,
        account_number=cmd.account_number,
        label=cmd.label,
    )
    return BankAccountResponse.model_validate(account)
