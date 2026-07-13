"""C2.1 — saldos USD vêm de ``exposicao_cambial.detalhes``, não do glob de disco morto.

Pós-ADR-212 os artifacts são DB-only; o glob sobre ``processed/E3_reconciled/*``
retornava vazio → USD zerado na narrativa ("US$ 0"). Fonte viva: ``exposicao_cambial``.
"""

from __future__ import annotations

from scripts.generate_narratives import _compute_usd_saldos_per_bank


def test_usd_saldos_from_exposicao_cambial():
    e5 = {
        "exposicao_cambial": {
            "detalhes": [
                {"fonte": "Bankofamerica (extratoconta)", "moeda": "USD", "saldo_original": 2605.0},
                {"fonte": "Wise (extratoconta)", "moeda": "USD", "saldo_original": 500.0},
                {"fonte": "Itau", "moeda": "BRL", "saldo_original": 1000.0},
            ]
        }
    }
    out = _compute_usd_saldos_per_bank(e5)
    assert out["total_usd"] == 3105.0
    assert out["bank_of_america_usd"] == 2605.0
    assert out["wise_usd"] == 500.0


def test_usd_saldos_ignora_nao_usd_e_saldo_invalido():
    e5 = {
        "exposicao_cambial": {
            "detalhes": [
                {"fonte": "Wise", "moeda": "EUR", "saldo_original": 100.0},
                {"fonte": "Bofa", "moeda": "USD", "saldo_original": None},
            ]
        }
    }
    assert _compute_usd_saldos_per_bank(e5)["total_usd"] == 0.0


def test_usd_saldos_vazio_sem_exposicao():
    assert _compute_usd_saldos_per_bank({})["total_usd"] == 0.0
