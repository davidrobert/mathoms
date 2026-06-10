"""ADR-282 slice 2 — dual-write do read-path: override manual (``create_override``)
e apply de regra (``_apply_engine``) populam ``natural_key_hash`` v2 + snapshot da
linha E4, sem mudar o match (segue em ``transaction_hash`` legado, flag off)."""

from __future__ import annotations

import importlib
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.application.categorization._apply_engine import (
    _ApplyCtx,
    _build_override_values,
)
from backend.app.application.transaction.create_override import create_override
from backend.app.models.transaction_override import TransactionOverride
from backend.app.schemas.transactions import TransactionItem, TransactionOverrideRequest
from backend.app.services.override_dual_read import OverrideMatchIndex
from backend.app.services.override_identity import identity_from_transaction_item
from backend.tests import factories


def _item(**over) -> TransactionItem:
    base = dict(
        data="2026-03-15",
        descricao="PIX MERCADO PAGO IFOOD",
        valor=Decimal("42.5"),
        banco="c6bank",
        categoria="Alimentacao",
        tipo_conta="conta_corrente",
        titular="Test User",
        moeda="BRL",
        tipo="debito",
        transaction_hash="legacyhash",
        row_id="legacyhash:0",
    )
    base.update(over)
    return TransactionItem(**base)


class _Rule:
    id = "rule-1"
    target_category = "Delivery"


def _assert_v2(get, expected) -> None:
    """``get`` lê coluna do override (attr ou key) e compara com a identidade v2."""
    assert get("natural_key_hash") == expected.natural_key_hash
    assert get("hash_version") == 2
    assert get("tx_direction") == "debit"
    assert get("tx_valor_cents") == 4250


@pytest.mark.asyncio
async def test_create_override_dual_writes_natural_key_v2(db, monkeypatch):
    ws = await factories.make_workspace(db)
    await db.commit()
    item = _item()
    mod = importlib.import_module("backend.app.application.transaction.create_override")
    monkeypatch.setattr(mod, "load_transactions", lambda *a, **k: [item])

    await create_override(
        ws.id, item.transaction_hash, TransactionOverrideRequest(new_category="Delivery"), db=db
    )
    await db.commit()

    override = (
        await db.execute(
            select(TransactionOverride).where(TransactionOverride.workspace_id == ws.id)
        )
    ).scalar_one()
    assert override.transaction_hash == item.transaction_hash  # legado preservado
    assert override.orphaned_at is None
    _assert_v2(lambda c: getattr(override, c), identity_from_transaction_item(item))


def test_apply_engine_build_override_values_includes_v2_columns():
    """``_build_override_values`` (apply de regra) carrega colunas v2 — paridade learning loop."""
    item = _item()
    ctx = _ApplyCtx(
        workspace_id="ws-1",
        rule=_Rule(),
        detector=None,
        db=None,
        closed_cache={},
        match_index=OverrideMatchIndex(workspace_id="ws-1", v2_enabled=False),
    )
    values = _build_override_values(item, ctx)
    _assert_v2(values.__getitem__, identity_from_transaction_item(item))
