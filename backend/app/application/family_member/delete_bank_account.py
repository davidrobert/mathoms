"""Use case: deletar conta bancária."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)


async def delete_bank_account(
    member_id: str,
    account_id: str,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
) -> None:
    """Garante membro+conta existem antes de deletar."""
    member = await repo.get_by_id(workspace_id, member_id)
    if not member:
        raise NotFoundError("Membro não encontrado", code="member_not_found")
    account = await repo.get_account(member_id, account_id)
    if not account:
        raise NotFoundError("Conta bancária não encontrada", code="account_not_found")
    await repo.delete_account(account)
