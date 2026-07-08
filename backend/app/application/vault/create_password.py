"""Use case: cifra e persiste um password novo no workspace."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.password_vault import PasswordVault
from backend.app.schemas.vault import VaultCreateRequest, VaultResponse
from backend.app.services.security.vault import VaultService


async def create_password(
    workspace_id: str,
    body: VaultCreateRequest,
    *,
    db: AsyncSession,
    vault: VaultService,
) -> VaultResponse:
    entry = PasswordVault(
        workspace_id=workspace_id,
        label=body.label,
        encrypted_password=vault.encrypt(body.password),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return VaultResponse.model_validate(entry)
