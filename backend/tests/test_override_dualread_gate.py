"""ADR-282 §Emenda / A26.l4 — persistência do gate da M2 (``persist_dualread_snapshot``)
+ wiring nos consumidores E4-reprocess (apply engine + learning loop). Os testes unitários
de match/shadow-compare do índice vivem em ``test_override_dual_read.py``; aqui é o que
toca ``AuditLog`` + os call-sites. Helpers compartilhados reusados do módulo irmão."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models.audit_log import AuditLog
from backend.app.services.audit import AuditAction
from backend.app.services.categorization_learning_loop import apply_learning_loop
from backend.app.services.override_dual_read import (
    OverrideMatchIndex,
    persist_dualread_snapshot,
)
from backend.app.services.override_identity import identity_from_classified_tx
from backend.tests.test_override_dual_read import (
    _apply_rule_sync,
    _classified,
    _insert_rule,
    _item,
    _persisted_override,
    _v2_of,
    _ws_with_flag,
)


def _snapshot_rows(sync_db, ws_id: str) -> list:
    stmt = select(AuditLog).where(
        AuditLog.workspace_id == ws_id,
        AuditLog.action == AuditAction.override_v2_dualread_snapshot.value,
    )
    return list(sync_db.execute(stmt).scalars().all())


# -- persist_dualread_snapshot (drena contadores per-request para AuditLog) --


def test_persist_snapshot_noop_when_v2_disabled() -> None:
    """Flag-OFF: nada a auditar (v2 nem rodou)."""
    index = OverrideMatchIndex(workspace_id="ws", v2_enabled=False)
    with SyncSessionLocal() as sync_db:
        persist_dualread_snapshot(sync_db, index)
        sync_db.commit()
        assert _snapshot_rows(sync_db, "ws") == []


@pytest.mark.asyncio
async def test_persist_snapshot_writes_audit_row_when_v2_ran(db) -> None:
    """Após exercício real do v2, o dreno grava 1 linha de AuditLog com as contagens (PII-zero)."""
    ws = await _ws_with_flag(db, enabled=True)
    item = _item(transaction_hash="v1-atual")
    ov = _persisted_override(ws.id, transaction_hash="v1-drifted", natural_key_hash=_v2_of(item))
    index = OverrideMatchIndex.from_overrides([ov], workspace_id=ws.id, v2_enabled=True)
    index.match(natural_key_hash=_v2_of(item), legacy_hash="v1-atual")

    with SyncSessionLocal() as sync_db:
        persist_dualread_snapshot(sync_db, index)
        sync_db.commit()
        rows = _snapshot_rows(sync_db, ws.id)
    assert len(rows) == 1
    assert rows[0].details == {"v1_fallback": 0, "v2_match": 1, "divergence": 0}


# -- wiring nos consumidores E4-reprocess (A26.l4 PR-2) --


@pytest.mark.asyncio
async def test_learning_loop_drains_snapshot_to_audit_log(db):
    """apply_learning_loop sob v2-ON drena o snapshot do índice para AuditLog (gate M2)."""
    ws = await _ws_with_flag(db, enabled=True)
    v2 = identity_from_classified_tx(_classified()).natural_key_hash
    db.add(_persisted_override(ws.id, transaction_hash="v1-drifted", natural_key_hash=v2))
    await db.commit()
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="PAGAMENTO", target="Compras")
        sync_db.commit()
        apply_learning_loop(
            workspace_id=ws.id, classified=[_classified(rule_id=rule.id)], db=sync_db
        )
        sync_db.commit()
        rows = _snapshot_rows(sync_db, ws.id)
    assert len(rows) == 1
    assert rows[0].details["v2_match"] >= 1


@pytest.mark.asyncio
async def test_apply_engine_drains_snapshot_to_audit_log(db):
    """apply_retroactive_sync sob v2-ON drena o snapshot do índice para AuditLog (gate M2)."""
    ws = await _ws_with_flag(db, enabled=True)
    item = _item(transaction_hash="v1-atual")
    db.add(_persisted_override(ws.id, transaction_hash="v1-drifted", natural_key_hash=_v2_of(item)))
    await db.commit()
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="PAGAMENTO", target="Compras")
        sync_db.commit()
        _apply_rule_sync(sync_db, ws_id=ws.id, rule=rule, item=item)
        sync_db.commit()
        rows = _snapshot_rows(sync_db, ws.id)
    assert len(rows) == 1
    assert rows[0].details["v2_match"] >= 1


@pytest.mark.asyncio
async def test_apply_engine_flag_off_drains_nothing(db):
    """Flag-OFF: nenhum snapshot (persist é no-op sem v2) — zero mudança de comportamento."""
    ws = await _ws_with_flag(db, enabled=False)
    item = _item(transaction_hash="v1-atual")
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="PAGAMENTO", target="Compras")
        sync_db.commit()
        _apply_rule_sync(sync_db, ws_id=ws.id, rule=rule, item=item)
        sync_db.commit()
        assert _snapshot_rows(sync_db, ws.id) == []
