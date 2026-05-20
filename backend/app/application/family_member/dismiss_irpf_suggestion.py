"""ADR-229 — use case ``dismiss_irpf_suggestion`` (descarte idempotente)."""

from __future__ import annotations

from typing import Optional

from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)
from backend.app.schemas.dto.family_member import IrpfDismissCommand


async def dismiss_irpf_suggestion(
    cmd: IrpfDismissCommand,
    *,
    workspace_id: str,
    repo: FamilyMemberRepositoryProtocol,
    actor_user_id: Optional[str] = None,
) -> None:
    """Persiste o descarte; idempotente em re-submit do mesmo (ws, year, inst, num)."""
    await repo.add_irpf_dismissal(
        workspace_id=workspace_id,
        irpf_year=cmd.irpf_year,
        institution_code=cmd.institution_code,
        account_number_norm=cmd.account_number_norm,
        member_key=cmd.member_key,
        created_by_user_id=actor_user_id,
    )
