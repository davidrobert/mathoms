"""Use case: remove password do workspace (falha 404 se não existir)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base import NotFoundError
from backend.app.models.password_vault import PasswordVault


async def delete_password(
    workspace_id: str, password_id: str, *, db: AsyncSession
) -> None:
    result = await db.execute(
        select(PasswordVault).where(
            PasswordVault.id == password_id,
            PasswordVault.workspace_id == workspace_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise NotFoundError("Senha não encontrada")
    await db.delete(entry)
    await db.commit()
