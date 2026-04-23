"""Helpers privados: carrega transações do disk/DB + aplica overrides + filtros."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction.filters import TransactionFilters
from backend.app.core.config import settings
from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.transaction_service import (
    apply_overrides,
    filter_transactions,
    load_transactions,
)


def _tenant_root(workspace_id: str) -> str:
    return str(settings.STORAGE_ROOT / workspace_id)


async def load_overrides_map(workspace_id: str, db: AsyncSession) -> dict[str, TransactionOverride]:
    result = await db.execute(
        select(TransactionOverride).where(TransactionOverride.workspace_id == workspace_id)
    )
    return {o.transaction_hash: o for o in result.scalars().all()}


async def load_filtered_transactions(
    workspace_id: str,
    filters: TransactionFilters,
    *,
    db: AsyncSession,
):
    transactions = load_transactions(workspace_id, _tenant_root(workspace_id))
    overrides_map = await load_overrides_map(workspace_id, db)
    transactions = apply_overrides(transactions, overrides_map)
    return filter_transactions(
        transactions,
        member=filters.member,
        bank=filters.bank,
        category=filters.category,
        date_from=filters.date_from,
        date_to=filters.date_to,
        value_min=filters.value_min,
        value_max=filters.value_max,
        search=filters.search,
    )


def tenant_root(workspace_id: str) -> str:
    return _tenant_root(workspace_id)
