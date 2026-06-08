"""ADR-282 slice 1 — dual-write do learning loop: ao criar ``TransactionOverride``
(``source='rule'``), o caminho popula ``natural_key_hash`` v2 + snapshot dos inputs,
sem mudar o match (que segue em ``transaction_hash`` legado enquanto a flag está off)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import OVERRIDE_SOURCE_RULE, TransactionOverride
from backend.app.services.categorization_learning_loop import apply_learning_loop
from backend.app.services.override_identity import identity_from_classified_tx
from backend.tests import factories
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction


def _insert_rule(
    db, *, workspace_id: str, keyword: str, target_category: str
) -> CategorizationRule:
    rule = CategorizationRule(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        keyword=keyword,
        target_category=target_category,
        priority=100,
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(rule)
    db.flush()
    return rule


def _make_tx(*, rule_id: str) -> ClassifiedTransaction:
    return ClassifiedTransaction(
        kind="despesa",
        data="2026-03-15",
        descricao="PIX MERCADO PAGO IFOOD",
        valor=42.5,
        banco="c6bank",
        moeda="BRL",
        tipo_conta="conta_corrente",
        titular="Test User",
        tipo="debito",
        categoria="Alimentacao",
        learned_rule_id=rule_id,
    )


def _apply_one_rule_override(sync_db, ws_id: str):
    """Arrange+act: 1 regra casa 1 tx → retorna (override persistido, identidade esperada)."""
    rule = _insert_rule(sync_db, workspace_id=ws_id, keyword="IFOOD", target_category="Alimentacao")
    sync_db.commit()
    tx = _make_tx(rule_id=rule.id)
    stats = apply_learning_loop(workspace_id=ws_id, classified=[tx], db=sync_db)
    sync_db.commit()
    assert stats.applied == 1
    override = sync_db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == ws_id,
            TransactionOverride.source == OVERRIDE_SOURCE_RULE,
        )
    ).scalar_one()
    return override, identity_from_classified_tx(tx)


@pytest.mark.asyncio
async def test_learning_loop_dual_writes_natural_key_v2(db):
    ws = await factories.make_workspace(db)
    await db.commit()
    with SyncSessionLocal() as sync_db:
        override, expected = _apply_one_rule_override(sync_db, ws.id)
        assert override.transaction_hash  # legado preservado (match enquanto flag off)
        assert override.natural_key_hash == expected.natural_key_hash
        assert override.hash_version == 2
        assert (override.tx_valor_cents, override.tx_direction, override.tx_moeda) == (
            4250,
            "debit",
            "BRL",
        )
        assert override.tx_descricao == "PIX MERCADO PAGO IFOOD"
        assert override.orphaned_at is None
