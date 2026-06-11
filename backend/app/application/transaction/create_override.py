"""Use case: cria ou atualiza TransactionOverride (upsert)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.application.transaction._loading import tenant_root
from backend.app.models.transaction_override import TransactionOverride
from backend.app.schemas.transactions import (
    TransactionOverrideRequest,
    TransactionOverrideResponse,
)
from backend.app.services.feature_flags_service import is_enabled
from backend.app.services.override_dual_read import (
    OVERRIDE_NATURAL_KEY_V2_FLAG,
    log_v1_fallback,
)
from backend.app.services.override_identity import (
    OverrideIdentity,
    identity_from_transaction_item,
)
from backend.app.services.transaction_service import load_transactions


async def _find_by_natural_key(
    workspace_id: str, natural_key_hash: str, *, db: AsyncSession
) -> Optional[TransactionOverride]:
    """Match v2 — só linhas ativas (semântica do índice parcial ADR-282 M1).
    Ordenação determinística cobre duplicata teórica (sem UK em v2)."""
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


async def _find_existing_dual_read(
    workspace_id: str,
    transaction_hash: str,
    identity: OverrideIdentity,
    *,
    db: AsyncSession,
) -> Optional[TransactionOverride]:
    """Dual-read v2→v1 sob flag-ON: sem ele, drift de v1 criaria duplicata (ADR-282)."""
    existing = await _find_by_natural_key(workspace_id, identity.natural_key_hash, db=db)
    if existing is not None:
        return existing
    existing = await _find_by_legacy_hash(workspace_id, transaction_hash, db=db)
    if existing is not None:
        log_v1_fallback(workspace_id)
    return existing


async def create_override(
    workspace_id: str,
    transaction_hash: str,
    body: TransactionOverrideRequest,
    *,
    db: AsyncSession,
) -> TransactionOverrideResponse:
    transactions = load_transactions(workspace_id, tenant_root(workspace_id))
    matching = [t for t in transactions if t.transaction_hash == transaction_hash]
    if not matching:
        raise NotFoundError("Transação não encontrada")
    original_category = matching[0].categoria
    # ADR-282 dual-write: hash v2 + snapshot da linha E4; flag-OFF mantém o
    # match no ``transaction_hash`` legado (zero-behavior).
    identity = identity_from_transaction_item(matching[0])

    v2_enabled = await is_enabled(workspace_id, OVERRIDE_NATURAL_KEY_V2_FLAG, db=db)
    if v2_enabled:
        existing = await _find_existing_dual_read(workspace_id, transaction_hash, identity, db=db)
    else:
        existing = await _find_by_legacy_hash(workspace_id, transaction_hash, db=db)

    if existing:
        existing.new_category = body.new_category
        existing.notes = body.notes
        existing.reviewed = True
        for column, value in identity.as_columns().items():
            setattr(existing, column, value)
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
        **identity.as_columns(),
    )
    db.add(override)
    await db.commit()
    await db.refresh(override)
    return TransactionOverrideResponse.model_validate(override)
