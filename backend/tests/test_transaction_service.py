"""Regressão: duplicatas físicas compartilham hash lógico mas têm row_id distinto."""

from __future__ import annotations

import pytest

from backend.app.services import transaction_service
from backend.app.services.transaction_service import load_transactions


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
    expected_hash = txs[0].transaction_hash
    assert [t.row_id for t in txs] == [f"{expected_hash}:{i}" for i in range(3)]


def test_distinct_transactions_get_distinct_hashes_and_row_ids(fake_artifacts):
    items = [_tx("Latte", "-12.50"), _tx("Uber", "-22.00", banco="itau", data="2026-04-16")]
    fake_artifacts[("categorize_transactions", "despesas")] = _payload(items)

    txs = load_transactions("ws-1", "/tmp/tenant")

    assert len({t.transaction_hash for t in txs}) == 2
    assert all(t.row_id == f"{t.transaction_hash}:0" for t in txs)


def test_row_id_counter_independent_across_categories(fake_artifacts):
    dup = _tx("Pix recebido", "100.00")
    fake_artifacts[("categorize_transactions", "receitas")] = _payload([dup, dict(dup)])

    txs = load_transactions("ws-1", "/tmp/tenant")

    assert len(txs) == 2
    assert len({t.row_id for t in txs}) == 2
