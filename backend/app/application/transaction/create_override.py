"""Use case: cria ou atualiza TransactionOverride (upsert)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.application.transaction._loading import tenant_root
from backend.app.models.transaction_override import TransactionOverride
from backend.app.schemas.transactions import (
    TransactionOverrideRequest,
    TransactionOverrideResponse,
)
from backend.app.services.transaction_service import load_transactions


async def create_override(
    workspace_id: str,
    transaction_hash: str,
    body: TransactionOverrideRequest,
    *,
    db: AsyncSession,
) -> TransactionOverrideResponse:
    transactions = load_transactions(tenant_root(workspace_id))
    matching = [t for t in transactions if t.transaction_hash == transaction_hash]
    if not matching:
        raise NotFoundError("Transação não encontrada")
    original_category = matching[0].categoria

    result = await db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == workspace_id,
            TransactionOverride.transaction_hash == transaction_hash,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.new_category = body.new_category
        existing.notes = body.notes
        existing.reviewed = True
        await db.commit()
        await db.refresh(existing)
        return TransactionOverrideResponse.model_validate(existing)

    override = TransactionOverride(
        workspace_id=workspace_id,
        transaction_hash=transaction_hash,
        original_category=original_category,
        new_category=body.new_category,
        notes=body.notes,
        reviewed=True,
    )
    db.add(override)
    await db.commit()
    await db.refresh(override)
    return TransactionOverrideResponse.model_validate(override)
