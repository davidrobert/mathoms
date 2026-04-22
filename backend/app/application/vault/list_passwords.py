"""Use case: lista passwords cifrados do workspace (metadados apenas)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.password_vault import PasswordVault
from backend.app.schemas.vault import VaultListResponse, VaultResponse


async def list_passwords(
    workspace_id: str, *, db: AsyncSession
) -> VaultListResponse:
    result = await db.execute(
        select(PasswordVault)
        .where(PasswordVault.workspace_id == workspace_id)
        .order_by(PasswordVault.created_at.desc())
    )
    entries = result.scalars().all()
    return VaultListResponse(
        passwords=[VaultResponse.model_validate(e) for e in entries],
        total=len(entries),
    )
