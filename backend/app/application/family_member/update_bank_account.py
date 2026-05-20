"""Use case: atualizar conta bancária (PUT com replace completo)."""

from __future__ import annotations

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)
from backend.app.application.family_member._uniqueness import check_account_collision
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
    """Garante membro+conta existem; check UNIQUE proativo (ADR-226 PR4)."""
    member = await repo.get_by_id(workspace_id, member_id)
    if not member:
        raise NotFoundError("Membro não encontrado", code="member_not_found")
    account = await repo.get_account(member_id, account_id)
    if not account:
        raise NotFoundError("Conta bancária não encontrada", code="account_not_found")
    collision = await check_account_collision(
        repo,
        workspace_id=workspace_id,
        institution_code=cmd.institution_code,
        account_number=cmd.account_number,
        exclude_account_id=account_id,
    )
    if collision is not None:
        raise ConflictError(
            f"Já existe conta em {cmd.institution_code} para {collision} — "
            "informe outro número da conta.",
            code="account_already_registered",
        )
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
