"""Use case: remove TransactionOverride do workspace."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.application.transaction._loading import tenant_root
from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.feature_flags_service import is_enabled
from backend.app.services.override_dual_read import (
    OVERRIDE_NATURAL_KEY_V2_FLAG,
    log_v1_fallback,
)
from backend.app.services.override_identity import identity_from_transaction_item
from backend.app.services.transaction_service import load_transactions


async def _find_by_legacy_hash(
    workspace_id: str, transaction_hash: str, *, db: AsyncSession
) -> Optional[TransactionOverride]:
    result = await db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == workspace_id,
            TransactionOverride.transaction_hash == transaction_hash,
        )
    )
    return result.scalar_one_or_none()


def _natural_key_for_wire_hash(workspace_id: str, transaction_hash: str) -> Optional[str]:
    """Recomputa o v2 da linha E4 que o FE referenciou — ``None`` se a linha sumiu."""
    transactions = load_transactions(workspace_id, tenant_root(workspace_id))
    matching = [t for t in transactions if t.transaction_hash == transaction_hash]
    if not matching:
        return None
    return identity_from_transaction_item(matching[0]).natural_key_hash


async def _find_by_natural_key(
    workspace_id: str, natural_key_hash: str, *, db: AsyncSession
) -> Optional[TransactionOverride]:
    """Match v2 só em linhas ativas; ordenação determinística (ADR-282)."""
    result = await db.execute(
        select(TransactionOverride)
        .where(
            TransactionOverride.workspace_id == workspace_id,
            TransactionOverride.natural_key_hash == natural_key_hash,
            TransactionOverride.deleted_at.is_(None),
        )
        .order_by(TransactionOverride.created_at.desc(), TransactionOverride.id)
    )
    return result.scalars().first()


async def _find_dual_read(
    workspace_id: str, transaction_hash: str, *, db: AsyncSession
) -> Optional[TransactionOverride]:
    """Dual-read v2→v1 sob flag-ON (ADR-282): v2 recomputado da linha E4;
    fallback v1 cobre override não-backfillado ou linha ausente do E4."""
    natural_key = _natural_key_for_wire_hash(workspace_id, transaction_hash)
    if natural_key is not None:
        via_v2 = await _find_by_natural_key(workspace_id, natural_key, db=db)
        if via_v2 is not None:
            return via_v2
    via_v1 = await _find_by_legacy_hash(workspace_id, transaction_hash, db=db)
    if via_v1 is not None:
        log_v1_fallback(workspace_id)
    return via_v1


async def delete_override(
    workspace_id: str,
    transaction_hash: str,
    *,
    db: AsyncSession,
) -> None:
    if await is_enabled(workspace_id, OVERRIDE_NATURAL_KEY_V2_FLAG, db=db):
        override = await _find_dual_read(workspace_id, transaction_hash, db=db)
    else:
        override = await _find_by_legacy_hash(workspace_id, transaction_hash, db=db)
    if override is None:
        raise NotFoundError("Override não encontrado")
    await db.delete(override)
    await db.commit()
