"""Sticky intra-run + ``_period_from_data`` contract — review fixes A12.P2 (ADR-186)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.app.core.database import SyncSessionLocal
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import OVERRIDE_SOURCE_RULE, TransactionOverride
from backend.app.services.categorization_learning_loop import (
    _period_from_data,
    apply_learning_loop,
)
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


def _make_tx(*, descricao: str, rule_id: str, categoria: str) -> ClassifiedTransaction:
    return ClassifiedTransaction(
        kind="despesa",
        data="2026-03-15",
        descricao=descricao,
        valor=50.0,
        banco="c6bank",
        moeda="BRL",
        tipo_conta="conta_corrente",
        titular="Test User",
        tipo="debito",
        categoria=categoria,
        learned_rule_id=rule_id,
    )


def _count_rule_overrides(db, ws_id: str) -> list[TransactionOverride]:
    from sqlalchemy import select

    return list(
        db.execute(
            select(TransactionOverride).where(
                TransactionOverride.workspace_id == ws_id,
                TransactionOverride.source == OVERRIDE_SOURCE_RULE,
            )
        ).scalars()
    )


def _setup_two_competing_rules(sync_db, ws_id):
    rule_a = _insert_rule(
        sync_db, workspace_id=ws_id, keyword="MERCADO PAGO IFOOD", target_category="Alimentacao"
    )
    rule_b = _insert_rule(sync_db, workspace_id=ws_id, keyword="IFOOD", target_category="Lazer")
    sync_db.commit()
    desc = "PIX MERCADO PAGO IFOOD"
    txs = [
        _make_tx(descricao=desc, rule_id=rule_a.id, categoria="Alimentacao"),
        _make_tx(descricao=desc, rule_id=rule_b.id, categoria="Lazer"),
    ]
    stats = apply_learning_loop(workspace_id=ws_id, classified=txs, db=sync_db)
    sync_db.commit()
    sync_db.refresh(rule_a)
    sync_db.refresh(rule_b)
    return rule_a, rule_b, stats


@pytest.mark.asyncio
async def test_sticky_intra_run_first_rule_wins(db):
    """Duas regras casando mesma txn → 1ª (sort) ganha; 2ª = skipped_sticky."""
    ws = await factories.make_workspace(db)
    await db.commit()
    with SyncSessionLocal() as sync_db:
        rule_a, rule_b, stats = _setup_two_competing_rules(sync_db, ws.id)
        overrides = _count_rule_overrides(sync_db, ws.id)
        assert len(overrides) == 1
        assert overrides[0].rule_id == rule_a.id
        assert overrides[0].new_category == "Alimentacao"
        assert (rule_a.applied_count, rule_b.applied_count) == (1, 0)
        assert stats.to_dict() == {
            "matches_total": 2,
            "applied": 1,
            "skipped_sticky": 1,
            "skipped_closed_month": 0,
        }


def test_period_from_data_returns_yyyymm_without_hyphen():
    assert _period_from_data("2026-03-15") == "202603"


def test_period_from_data_returns_none_for_invalid_input():
    assert _period_from_data("") is None
    assert _period_from_data("abc-de-fg") is None
    assert _period_from_data("20") is None


# ─────────────────────────────────────────────────────────────────────
# ADR-188 §D4 — INSERT ... ON CONFLICT race protection
# ─────────────────────────────────────────────────────────────────────


def _race_setup(sync_db, ws_id):
    rule = _insert_rule(
        sync_db,
        workspace_id=ws_id,
        keyword="MERCADO PAGO IFOOD",
        target_category="Alimentacao",
    )
    sync_db.commit()
    tx = _make_tx(
        descricao="PIX MERCADO PAGO IFOOD",
        rule_id=rule.id,
        categoria="Alimentacao",
    )
    return rule, tx


def _run_two_concurrent_sessions(ws_id: str, tx) -> tuple:
    """2 sessions sequenciais simulam pre-load anterior ao commit da outra."""
    with SyncSessionLocal() as s1, SyncSessionLocal() as s2:
        stats_1 = apply_learning_loop(workspace_id=ws_id, classified=[tx], db=s1)
        s1.commit()
        stats_2 = apply_learning_loop(workspace_id=ws_id, classified=[tx], db=s2)
        s2.commit()
    return stats_1, stats_2


@pytest.mark.asyncio
async def test_on_conflict_safety_net_simulated_concurrent_insert(db):
    """2 sessions paralelas → 1 override final (sem IntegrityError) — ADR-188 §D4."""
    ws = await factories.make_workspace(db)
    await db.commit()
    with SyncSessionLocal() as setup_db:
        rule, tx = _race_setup(setup_db, ws.id)
    stats_1, stats_2 = _run_two_concurrent_sessions(ws.id, tx)
    assert stats_1.applied == 1
    # s2 também conta como applied (executou INSERT), mas o ON CONFLICT
    # converteu em UPDATE — não duplicou linha.
    assert stats_2.applied == 1
    with SyncSessionLocal() as check_db:
        overrides = _count_rule_overrides(check_db, ws.id)
        assert len(overrides) == 1
        assert overrides[0].rule_id == rule.id
        assert overrides[0].new_category == "Alimentacao"


def _seed_manual_override(sync_db, ws_id: str, tx_seed) -> None:
    """Insere manual override para o hash de ``tx_seed`` antes do loop rodar."""
    from backend.app.services.categorization_learning_loop import _tx_hash

    manual = TransactionOverride(
        workspace_id=ws_id,
        transaction_hash=_tx_hash(tx_seed),
        original_category="Alimentacao",
        new_category="Alimentacao",
        source="manual",
        rule_id=None,
        reviewed=True,
    )
    sync_db.add(manual)
    sync_db.commit()


def _list_overrides(sync_db, ws_id: str) -> list[TransactionOverride]:
    from sqlalchemy import select

    return list(
        sync_db.execute(
            select(TransactionOverride).where(TransactionOverride.workspace_id == ws_id)
        ).scalars()
    )


@pytest.mark.asyncio
async def test_on_conflict_does_not_overwrite_manual(db):
    """Manual override → rule INSERT cai em sticky-skip; manual intocado (ADR-186 §D2)."""
    ws = await factories.make_workspace(db)
    await db.commit()
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="IFOOD", target_category="Lazer")
        tx_seed = _make_tx(descricao="PIX IFOOD", rule_id=rule.id, categoria="Lazer")
        _seed_manual_override(sync_db, ws.id, tx_seed)
        stats = apply_learning_loop(workspace_id=ws.id, classified=[tx_seed], db=sync_db)
        sync_db.commit()
        rows = _list_overrides(sync_db, ws.id)
        assert len(rows) == 1
        assert rows[0].source == "manual"
        assert rows[0].new_category == "Alimentacao"
        assert stats.skipped_sticky == 1
        assert stats.applied == 0
