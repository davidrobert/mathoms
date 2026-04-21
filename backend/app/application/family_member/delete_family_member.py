"""Use case: deletar membro (cascade de bank_accounts no repo)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)


async def delete_family_member(
    member_id: str,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
) -> None:
    """Remove o membro e suas contas bancárias (cascade no repo)."""
    member = await repo.get_by_id(workspace_id, member_id)
    if not member:
        raise NotFoundError("Membro não encontrado", code="member_not_found")
    await repo.delete(member)
