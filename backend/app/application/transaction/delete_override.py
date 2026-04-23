"""Use case: remove TransactionOverride do workspace."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.models.transaction_override import TransactionOverride


async def delete_override(
    workspace_id: str,
    transaction_hash: str,
    *,
    db: AsyncSession,
) -> None:
    result = await db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == workspace_id,
            TransactionOverride.transaction_hash == transaction_hash,
        )
    )
    override = result.scalar_one_or_none()
    if override is None:
        raise NotFoundError("Override não encontrado")
    await db.delete(override)
    await db.commit()
