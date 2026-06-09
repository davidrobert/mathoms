"""Gate de paridade B5 (ADR-278): ``amount`` decimal espelha ``valor`` no contrato E2.
Roda ``stamp_natural_key`` sobre payloads E2 representativos e prova que, enquanto
``valor`` (float) e ``amount`` (decimal string) coexistem na janela de migração de
2 fases, concordam em centavos — invariante que sustenta a aditividade (G1) e protege
o cutover futuro ``valor``→``amount`` (A24). ``amount`` NÃO é consumido nesta onda."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from pipeline.domain.services._tx_identity import decimal_cents
from pipeline.domain.services.e2_natural_key import stamp_natural_key

_REPO = Path(__file__).resolve().parents[1]
_E2_GOLDEN_DIR = _REPO / "tests" / "fixtures" / "pipeline_golden" / "e2"
_E2_FIXTURES = sorted(_E2_GOLDEN_DIR.glob("*-2_extract.json"))


def _assert_amount_parity(txs: list[dict]) -> int:
    checked = 0
    for tx in txs:
        valor = tx.get("valor")
        if valor is None:
            assert "amount" not in tx
            continue
        assert "amount" in tx, f"valor presente sem amount: {tx}"
        assert decimal_cents(tx["amount"]) == decimal_cents(valor)
        assert Decimal(tx["amount"]) == Decimal(str(valor))
        checked += 1
    return checked


@pytest.mark.parametrize("fixture", _E2_FIXTURES, ids=lambda p: p.name)
def test_amount_parity_over_golden_e2(fixture: Path):
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    stamp_natural_key(payload)
    _assert_amount_parity(payload.get("transacoes") or [])


def test_amount_parity_synthetic_battery():
    # Bordas que os parsers de banco emitem: positivo/negativo, FX 3 casas, grande, zero.
    payload = {
        "banco": "C6",
        "moeda": "BRL",
        "titular": "ana",
        "tipo_conta": "corrente",
        "transacoes": [
            {"data": "2026-01-01", "descricao": "pix", "valor": 100.0},
            {"data": "2026-01-02", "descricao": "saque", "valor": -1234.56},
            {"data": "2026-01-03", "descricao": "fx", "valor": 0.575},
            {"data": "2026-01-04", "descricao": "grande", "valor": 1e15},
            {"data": "2026-01-05", "descricao": "zero", "valor": 0.0},
        ],
    }
    stamp_natural_key(payload)
    txs = payload["transacoes"]
    assert _assert_amount_parity(txs) == 5
    assert all("E" not in tx["amount"] and "e" not in tx["amount"] for tx in txs)
