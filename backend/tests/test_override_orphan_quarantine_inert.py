"""Quarentena de override é terminal e INERTE (ADR-282 §5) — regressão do gate
A26.l4: órfão (``orphaned_at`` set) seguia casando via ``transaction_hash`` v1 em
todos os índices de match, poluindo ``v1_fallback`` (4/0/0 em 9 snapshots do
dogfood) e sticky-bloqueando learned rule. O drop da Fase E removeria esse
comportamento silenciosamente — os índices devem excluir o órfão JÁ."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.application.categorization.rule_preview_service import (
    _load_active_manual_index,
)
from backend.app.application.transaction._loading import load_override_index
from backend.app.core.database import SyncSessionLocal
from backend.app.services.categorization_learning_loop import _tx_hash, apply_learning_loop
from backend.tests.test_override_dual_read import (
    _apply_rule_sync,
    _classified,
    _insert_rule,
    _item,
    _persisted_override,
    _ws_with_flag,
)
from backend.tests.test_override_dualread_gate import _snapshot_rows


def _quarantined(ws_id: str, *, transaction_hash: str, **over):
    return _persisted_override(
        ws_id,
        transaction_hash=transaction_hash,
        natural_key_hash=None,
        orphaned_at=datetime.now(timezone.utc),
        **over,
    )


@pytest.mark.asyncio
async def test_learning_loop_ignores_quarantined_override(db):
    """Órfão com o MESMO v1 da tx da rule não conta v1_fallback nem sticky-bloqueia."""
    ws = await _ws_with_flag(db, enabled=True)
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="PAGAMENTO", target="Compras")
        sync_db.flush()
        tx = _classified(rule_id=rule.id)
        sync_db.add(_quarantined(ws.id, transaction_hash=_tx_hash(tx)))
        sync_db.commit()

        stats = apply_learning_loop(workspace_id=ws.id, classified=[tx], db=sync_db)
        sync_db.commit()

        assert stats.to_dict()["applied"] == 1
        assert stats.to_dict()["skipped_sticky"] == 0
        # contadores zerados → dreno no-op (pré-fix: v1_fallback=1 gravava snapshot)
        assert _snapshot_rows(sync_db, ws.id) == []


@pytest.mark.asyncio
async def test_readpath_index_excludes_quarantined_override(db):
    """GET /transactions não aplica categoria de override quarentenado (v1 nem v2)."""
    ws = await _ws_with_flag(db, enabled=True)
    item = _item()
    db.add(_quarantined(ws.id, transaction_hash=item.transaction_hash))
    await db.commit()

    index = await load_override_index(ws.id, db)

    assert index.by_legacy_hash == {}
    assert index.by_natural_key == {}


@pytest.mark.asyncio
async def test_apply_engine_orphan_does_not_sticky_block(db):
    """Apply retroativo de rule ignora órfão manual com o mesmo v1 (aplica em vez de sticky)."""
    ws = await _ws_with_flag(db, enabled=True)
    item = _item()
    db.add(_quarantined(ws.id, transaction_hash=item.transaction_hash))
    await db.commit()
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="PAGAMENTO", target="Compras")
        sync_db.commit()

        applied = _apply_rule_sync(sync_db, ws_id=ws.id, rule=rule, item=item)

        assert applied == 1


@pytest.mark.asyncio
async def test_rule_preview_manual_index_excludes_quarantined(db):
    """Preview de rule não trata órfão manual como sticky."""
    ws = await _ws_with_flag(db, enabled=True)
    item = _item()
    db.add(_quarantined(ws.id, transaction_hash=item.transaction_hash))
    await db.commit()
    with SyncSessionLocal() as sync_db:
        index = _load_active_manual_index(sync_db, ws.id, v2_enabled=True)

    assert index.by_legacy_hash == {}
