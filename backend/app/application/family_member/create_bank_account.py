"""Use case: criar conta bancária vinculada a um membro."""

from __future__ import annotations

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)
from backend.app.application.family_member._uniqueness import (
    check_account_collision,
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
    """Valida membership e adiciona a conta (ADR-226 PR4: check UNIQUE proativo)."""
    member = await repo.get_by_id(workspace_id, member_id)
    if not member:
        raise NotFoundError("Membro não encontrado", code="member_not_found")
    collision = await check_account_collision(
        repo,
        workspace_id=workspace_id,
        institution_code=cmd.institution_code,
        account_number=cmd.account_number,
        exclude_member_id=None,
        exclude_account_id=None,
    )
    if collision is not None:
        raise ConflictError(
            f"Já existe conta em {cmd.institution_code} para {collision} — "
            "informe o número da conta para diferenciar.",
            code="account_already_registered",
        )
    account = await repo.add_account(
        member_id,
        workspace_id=workspace_id,
        institution_code=cmd.institution_code,
        account_type=cmd.account_type,
        agency=cmd.agency,
        account_number=cmd.account_number,
        label=cmd.label,
        is_joint=cmd.is_joint,
        co_titulares=cmd.co_titulares,
    )
    return BankAccountResponse.model_validate(account)
