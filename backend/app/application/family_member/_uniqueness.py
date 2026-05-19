"""Check UNIQUE proativo de bank_account no boundary do use case (ADR-226 PR4)."""

from __future__ import annotations

from typing import Optional

from backend.app.application.family_member._protocols import FamilyMemberRepositoryProtocol
from pipeline.domain.services.account_normalization import normalize_account_number


def _is_conflict(acc, m, *, institution_code, norm, exclude_account_id, exclude_member_id) -> bool:
    if acc.institution_code != institution_code:
        return False
    if normalize_account_number(acc.account_number) != norm:
        return False
    if exclude_account_id is not None and acc.id == exclude_account_id:
        return False
    same_member = exclude_member_id is not None and m.id == exclude_member_id
    return not (same_member and exclude_account_id is None)


def _find_conflict(members, **kw) -> Optional[str]:
    pairs = ((m, acc) for m in members for acc in m.accounts)
    return next((m.full_name for m, acc in pairs if _is_conflict(acc, m, **kw)), None)


async def check_account_collision(
    repo: FamilyMemberRepositoryProtocol,
    *,
    workspace_id: str,
    institution_code: str,
    account_number: Optional[str],
    exclude_member_id: Optional[str] = None,
    exclude_account_id: Optional[str] = None,
) -> Optional[str]:
    """Retorna `member.full_name` em conflito, ou None se livre (ADR-226 PR4)."""
    norm = normalize_account_number(account_number)
    if norm is None:
        return None
    return _find_conflict(
        await repo.list_by_workspace(workspace_id),
        institution_code=institution_code,
        norm=norm,
        exclude_account_id=exclude_account_id,
        exclude_member_id=exclude_member_id,
    )
