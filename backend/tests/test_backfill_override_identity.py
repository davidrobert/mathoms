"""ADR-282 slice 3 — backfill reancora overrides legados ao natural_key v2:
reanchor limpo, quarentena de órfão e de v1-ambíguo (1-velho→N-novo), precedência
de colisão (N-velho→1-novo), quiesce (run ativo aborta) e idempotência."""

from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    OVERRIDE_SOURCE_RULE,
    TransactionOverride,
)
from backend.app.schemas.transactions import TransactionItem
from backend.app.services.feature_flags_service import set_flag
from backend.app.services.internal_ops.backfill_override_identity import (
    backfill_override_identity,
    resolve_collision,
)
from backend.app.services.override_identity import identity_from_transaction_item
from backend.tests import factories

_MOD = "backend.app.services.internal_ops.backfill_override_identity"
_NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _item(tx_hash: str, **over) -> TransactionItem:
    base = dict(
        data="2026-03-15",
        descricao="PAGAMENTO LOJA",
        valor="50.0",
        banco="c6bank",
        categoria="Lazer",
        tipo_conta="conta_corrente",
        titular="Test User",
        moeda="BRL",
        tipo="debito",
        transaction_hash=tx_hash,
        row_id=f"{tx_hash}:0",
    )
    base.update(over)
    return TransactionItem(**base)


def _override(ws_id: str, tx_hash: str, *, source: str = OVERRIDE_SOURCE_MANUAL, **over):
    base = dict(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        transaction_hash=tx_hash,
        original_category="Lazer",
        new_category="Delivery",
        source=source,
        reviewed=True,
        created_at=_NOW,
    )
    base.update(over)
    return TransactionOverride(**base)


def _patch_e4(monkeypatch, items: list[TransactionItem]) -> None:
    mod = importlib.import_module(_MOD)
    monkeypatch.setattr(mod, "load_transactions", lambda *a, **k: items)


async def _precutover_workspace(db):
    """Workspace na janela pré-cutover: backfill exige a flag v2 OFF (_preflight)."""
    ws = await factories.make_workspace(db)
    await set_flag(ws.id, "override_natural_key_v2_enabled", False, db=db)
    return ws


async def _fetch_all(db, ws_id: str) -> list[TransactionOverride]:
    stmt = select(TransactionOverride).where(TransactionOverride.workspace_id == ws_id)
    return list((await db.execute(stmt)).scalars().all())


async def _fetch_one(db, ws_id: str) -> TransactionOverride:
    return (await _fetch_all(db, ws_id))[0]


# -- resolve_collision (puro) --


def _ovr(source: str, created_at: datetime, oid: str) -> TransactionOverride:
    return TransactionOverride(id=oid, source=source, created_at=created_at)


def test_resolve_collision_manual_beats_rule() -> None:
    rule = _ovr(OVERRIDE_SOURCE_RULE, _NOW + timedelta(days=1), "a")
    manual = _ovr(OVERRIDE_SOURCE_MANUAL, _NOW, "b")
    winner, losers = resolve_collision([rule, manual])
    assert winner.id == "b"
    assert [o.id for o in losers] == ["a"]


def test_resolve_collision_recent_then_id_breaks_tie() -> None:
    old = _ovr(OVERRIDE_SOURCE_MANUAL, _NOW, "z")
    new = _ovr(OVERRIDE_SOURCE_MANUAL, _NOW + timedelta(days=1), "y")
    tie = _ovr(OVERRIDE_SOURCE_MANUAL, _NOW + timedelta(days=1), "a")
    winner, losers = resolve_collision([old, new, tie])
    assert winner.id == "a"  # mesmo created_at de "y" → id desempata
    assert [o.id for o in losers] == ["y", "z"]


# -- backfill (DB) --


@pytest.mark.asyncio
async def test_backfill_reanchors_legacy_override(db, monkeypatch):
    ws = await _precutover_workspace(db)
    item = _item("v1hash")
    db.add(_override(ws.id, "v1hash"))
    await db.commit()
    _patch_e4(monkeypatch, [item])

    result = await backfill_override_identity(db, workspace_id=ws.id, actor="op", preview=False)
    await db.commit()

    assert result.ok and result.details["reanchored"] == 1
    ovr = await _fetch_one(db, ws.id)
    assert ovr.natural_key_hash == identity_from_transaction_item(item).natural_key_hash
    assert ovr.orphaned_at is None


@pytest.mark.asyncio
async def test_backfill_orphans_when_v1_absent(db, monkeypatch):
    ws = await _precutover_workspace(db)
    db.add(_override(ws.id, "missing_v1"))
    await db.commit()
    _patch_e4(monkeypatch, [_item("other_v1")])

    result = await backfill_override_identity(db, workspace_id=ws.id, actor="op", preview=False)
    await db.commit()

    assert result.details["orphaned"] == 1
    ovr = await _fetch_one(db, ws.id)
    assert ovr.natural_key_hash is None and ovr.orphaned_at is not None


@pytest.mark.asyncio
async def test_backfill_quarantines_ambiguous_v1(db, monkeypatch):
    ws = await _precutover_workspace(db)
    db.add(_override(ws.id, "shared_v1"))
    await db.commit()
    # mesmo v1, tipo_conta divergente → 2 natural_keys v2 → 1-velho→N-novo (ambíguo)
    _patch_e4(
        monkeypatch,
        [
            _item("shared_v1", tipo_conta="conta_corrente"),
            _item("shared_v1", tipo_conta="conta_poupanca"),
        ],
    )

    result = await backfill_override_identity(db, workspace_id=ws.id, actor="op", preview=False)
    await db.commit()

    assert result.details["ambiguous"] == 1 and result.details["reanchored"] == 0
    ovr = await _fetch_one(db, ws.id)
    assert ovr.natural_key_hash is None and ovr.orphaned_at is not None


@pytest.mark.asyncio
async def test_backfill_collision_precedence(db, monkeypatch):
    ws = await _precutover_workspace(db)
    # 2 v1 distintos (drift PIX) → mesmo v2; manual vence rule
    plain, suffixed = _item("v1a"), _item("v1b", descricao="PAGAMENTO LOJA — TRANSF ENVIADA PIX")
    db.add(_override(ws.id, "v1a", source=OVERRIDE_SOURCE_RULE))
    db.add(_override(ws.id, "v1b", source=OVERRIDE_SOURCE_MANUAL))
    await db.commit()
    _patch_e4(monkeypatch, [plain, suffixed])

    result = await backfill_override_identity(db, workspace_id=ws.id, actor="op", preview=False)
    await db.commit()

    assert result.details["collided"] == 1
    rows = await _fetch_all(db, ws.id)
    winner = [r for r in rows if r.transaction_hash == "v1b"][0]
    loser = [r for r in rows if r.transaction_hash == "v1a"][0]
    assert winner.natural_key_hash is not None and winner.deleted_at is None
    assert loser.deleted_at is not None and "ADR-282" in (loser.notes or "")


@pytest.mark.asyncio
async def test_backfill_aborts_when_run_active(db, monkeypatch):
    ws = await _precutover_workspace(db)
    db.add(_override(ws.id, "v1hash"))
    db.add(PipelineRun(id=str(uuid.uuid4()), workspace_id=ws.id, status=PipelineRunStatus.running))
    await db.commit()
    _patch_e4(monkeypatch, [_item("v1hash")])

    result = await backfill_override_identity(db, workspace_id=ws.id, actor="op", preview=False)
    await db.commit()

    assert not result.ok and result.error == "workspace_busy"
    ovr = await _fetch_one(db, ws.id)
    assert ovr.natural_key_hash is None  # nada escrito


@pytest.mark.asyncio
async def test_backfill_preview_is_read_only(db, monkeypatch):
    ws = await _precutover_workspace(db)
    db.add(_override(ws.id, "v1hash"))
    await db.commit()
    _patch_e4(monkeypatch, [_item("v1hash")])

    result = await backfill_override_identity(db, workspace_id=ws.id, actor="op", preview=True)
    await db.commit()

    assert result.details["preview"] is True and result.details["reanchored"] == 1
    ovr = await _fetch_one(db, ws.id)
    assert ovr.natural_key_hash is None  # preview não escreve


@pytest.mark.asyncio
async def test_backfill_idempotent_rerun(db, monkeypatch):
    ws = await _precutover_workspace(db)
    db.add(_override(ws.id, "v1hash"))
    await db.commit()
    _patch_e4(monkeypatch, [_item("v1hash")])

    await backfill_override_identity(db, workspace_id=ws.id, actor="op", preview=False)
    await db.commit()
    second = await backfill_override_identity(db, workspace_id=ws.id, actor="op", preview=False)
    await db.commit()

    assert second.details == {
        "preview": False,
        "overrides_total": 0,
        "reanchored": 0,
        "orphaned": 0,
        "ambiguous": 0,
        "collided": 0,
    }
