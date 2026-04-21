"""Use case: listar contas bancárias de um membro."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)
from backend.app.schemas.dto.family_member import BankAccountResponse


async def list_bank_accounts(
    member_id: str,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
) -> list[BankAccountResponse]:
    """Garante que o membro pertence ao workspace antes de listar contas."""
    member = await repo.get_by_id(workspace_id, member_id)
    if not member:
        raise NotFoundError("Membro não encontrado", code="member_not_found")
    accounts = await repo.list_accounts(member_id)
    return [BankAccountResponse.model_validate(a) for a in accounts]
