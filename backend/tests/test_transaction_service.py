"""Regressão: duplicatas físicas compartilham hash lógico mas têm row_id distinto.

Pré-trabalho Fase E (ADR-282): ``row_id`` deriva da identidade v2
(``natural_key_hash``); ``transaction_hash`` v1 segue no wire p/ o dual-read.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    TransactionOverride,
)
from backend.app.services import transaction_service
from backend.app.services.override_dual_read import OverrideMatchIndex
from backend.app.services.override_identity import identity_from_transaction_item
from backend.app.services.transaction_service import apply_overrides, load_transactions


def _payload(items: list[dict]) -> dict:
    return {"dados": {"alimentacao": items}}


def _tx(descricao: str, valor: str, *, data: str = "2026-04-15", banco: str = "c6bank") -> dict:
    return {
        "data": data,
        "descricao": descricao,
        "valor": valor,
        "banco": banco,
        "titular": "David",
    }


@pytest.fixture
def fake_artifacts(monkeypatch):
    storage: dict[tuple[str, str], dict] = {}

    def fake_read(workspace_id, *, stage, key, tenant_root):  # noqa: ARG001
        return storage.get((stage, key))

    monkeypatch.setattr(transaction_service, "read_latest_artifact", fake_read)
    return storage


def test_duplicate_physical_transactions_get_unique_row_ids(fake_artifacts):
    dup = _tx("Latte", "-12.50")
    fake_artifacts[("categorize_transactions", "despesas")] = _payload([dup, dict(dup), dict(dup)])

    txs = load_transactions("ws-1", "/tmp/tenant")

    assert len(txs) == 3
    assert len({t.transaction_hash for t in txs}) == 1, "duplicatas devem compartilhar hash"
    expected_key = identity_from_transaction_item(txs[0]).natural_key_hash
    assert [t.row_id for t in txs] == [f"{expected_key}:{i}" for i in range(3)]


def test_distinct_transactions_get_distinct_hashes_and_row_ids(fake_artifacts):
    items = [_tx("Latte", "-12.50"), _tx("Uber", "-22.00", banco="itau", data="2026-04-16")]
    fake_artifacts[("categorize_transactions", "despesas")] = _payload(items)

    txs = load_transactions("ws-1", "/tmp/tenant")

    assert len({t.transaction_hash for t in txs}) == 2
    assert all(t.row_id == f"{identity_from_transaction_item(t).natural_key_hash}:0" for t in txs)


def test_row_id_counter_independent_across_categories(fake_artifacts):
    dup = _tx("Pix recebido", "100.00")
    fake_artifacts[("categorize_transactions", "receitas")] = _payload([dup, dict(dup)])

    txs = load_transactions("ws-1", "/tmp/tenant")

    assert len(txs) == 2
    assert len({t.row_id for t in txs}) == 2


# ─── Pré-trabalho Fase E (ADR-282): row_id ancorado na identidade v2 ──────


def test_row_id_derives_from_v2_and_is_stable_across_reloads(fake_artifacts):
    """row_id não depende de ``transaction_hash`` v1 — sobrevive ao drop da Fase E."""
    fake_artifacts[("categorize_transactions", "despesas")] = _payload(
        [_tx("Latte", "-12.50"), _tx("Uber", "-22.00")]
    )

    first = load_transactions("ws-1", "/tmp/tenant")
    second = load_transactions("ws-1", "/tmp/tenant")

    assert [t.row_id for t in first] == [t.row_id for t in second], "row_id deve ser determinístico"
    for t in first:
        base, _, idx = t.row_id.rpartition(":")
        assert base == identity_from_transaction_item(t).natural_key_hash
        assert idx == "0"
        assert base != t.transaction_hash, "base do row_id não pode ser o hash v1"


def _override_for(tx, *, new_category: str) -> TransactionOverride:
    """Espelha o dual-write de ``create_override`` (v1 + colunas v2, ADR-282)."""
    return TransactionOverride(
        id=str(uuid.uuid4()),
        transaction_hash=tx.transaction_hash,
        original_category=tx.categoria,
        new_category=new_category,
        source=OVERRIDE_SOURCE_MANUAL,
        reviewed=True,
        created_at=datetime.now(timezone.utc),
        deleted_at=None,
        **identity_from_transaction_item(tx).as_columns(),
    )


@pytest.mark.parametrize("v2_enabled", [True, False])
def test_override_created_from_new_row_id_applies_on_reload(fake_artifacts, v2_enabled):
    """FE identifica a linha pelo row_id novo, envia o ``transaction_hash`` que veio
    junto (contrato inalterado) e o override casa no reload — v2 e fallback v1."""
    fake_artifacts[("categorize_transactions", "despesas")] = _payload([_tx("Latte", "-12.50")])
    target = load_transactions("ws-1", "/tmp/tenant")[0]
    index = OverrideMatchIndex.from_overrides(
        [_override_for(target, new_category="Cafeteria")],
        workspace_id="ws-1",
        v2_enabled=v2_enabled,
    )

    reloaded = apply_overrides(load_transactions("ws-1", "/tmp/tenant"), index)

    overridden = [t for t in reloaded if t.row_id == target.row_id]
    assert len(overridden) == 1
    assert overridden[0].is_overridden
    assert overridden[0].categoria == "Cafeteria"


# ─── paginate_transactions: sort por impacto (A28.l5) ────────────────────


def _load(fake_artifacts, items: list[dict]):
    fake_artifacts[("categorize_transactions", "despesas")] = _payload(items)
    return load_transactions("ws-1", "/tmp/tenant")


def test_paginate_default_sorts_by_date_desc(fake_artifacts):
    from backend.app.services.transaction_service import paginate_transactions

    txs = _load(
        fake_artifacts,
        [
            _tx("Latte", "-12.50", data="2026-04-15"),
            _tx("Uber", "-22.00", data="2026-04-17"),
            _tx("Mercado", "-180.00", data="2026-04-16"),
        ],
    )

    page, summary = paginate_transactions(txs, 1, 50)

    assert [t.data for t in page] == ["2026-04-17", "2026-04-16", "2026-04-15"]
    assert summary.count == 3


def test_paginate_valor_desc_sorts_by_absolute_impact(fake_artifacts):
    from backend.app.services.transaction_service import paginate_transactions

    txs = _load(
        fake_artifacts,
        [
            _tx("Latte", "-12.50", data="2026-04-17"),
            _tx("Uber", "-22.00", data="2026-04-16"),
            _tx("Mercado", "-180.00", data="2026-04-15"),
        ],
    )

    page, _ = paginate_transactions(txs, 1, 50, sort="valor_desc")

    assert [t.descricao for t in page] == ["Mercado", "Uber", "Latte"]


def test_paginate_valor_desc_does_not_change_summary(fake_artifacts):
    from backend.app.services.transaction_service import paginate_transactions

    txs = _load(fake_artifacts, [_tx("Latte", "-12.50"), _tx("Uber", "-22.00")])

    _, by_date = paginate_transactions(txs, 1, 50)
    _, by_impact = paginate_transactions(txs, 1, 50, sort="valor_desc")

    assert by_impact == by_date
