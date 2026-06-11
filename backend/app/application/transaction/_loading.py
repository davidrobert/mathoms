"""Helpers privados: carrega transações do disk/DB + aplica overrides + filtros."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction.filters import TransactionFilters
from backend.app.core.config import settings
from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.feature_flags_service import is_enabled
from backend.app.services.override_dual_read import (
    OVERRIDE_NATURAL_KEY_V2_FLAG,
    OverrideMatchIndex,
)
from backend.app.services.transaction_service import (
    apply_overrides,
    filter_transactions,
    load_transactions,
)


def _tenant_root(workspace_id: str) -> str:
    return str(settings.STORAGE_ROOT / workspace_id)


async def load_override_index(workspace_id: str, db: AsyncSession) -> OverrideMatchIndex:
    # ADR-188 §D1 — soft-delete preserva histórico; read-path ignora linhas
    # com ``deleted_at IS NOT NULL`` para manter paridade com o pipeline.
    result = await db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == workspace_id,
            TransactionOverride.deleted_at.is_(None),
        )
    )
    v2_enabled = await is_enabled(workspace_id, OVERRIDE_NATURAL_KEY_V2_FLAG, db=db)
    return OverrideMatchIndex.from_overrides(
        result.scalars().all(), workspace_id=workspace_id, v2_enabled=v2_enabled
    )


async def load_filtered_transactions(
    workspace_id: str,
    filters: TransactionFilters,
    *,
    db: AsyncSession,
):
    transactions = load_transactions(workspace_id, _tenant_root(workspace_id))
    match_index = await load_override_index(workspace_id, db)
    transactions = apply_overrides(transactions, match_index)
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
