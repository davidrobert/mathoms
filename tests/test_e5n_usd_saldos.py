"""C2.1 + A37.l14 (PD-12) — saldos USD dinâmicos a partir de ``exposicao_cambial.detalhes``.

Pós-ADR-212 os artifacts são DB-only; o glob sobre ``processed/E3_reconciled/*``
retornava vazio → USD zerado na narrativa ("US$ 0"). Fonte viva: ``exposicao_cambial``.

PD-12: a enumeração era hardcoded (Wise/BofA) — uma 3ª conta USD entrava no
``total_usd`` mas sumia da narrativa s6, e a soma exibida não fechava.
"""

from __future__ import annotations

from pipeline.domain.services.narrativas.summaries_narrator import _fmt_usd_por_banco
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
    assert out["por_banco"] == {"Bank of America": 2605.0, "Wise": 500.0}


def test_usd_saldos_terceira_conta_entra_na_enumeracao():
    """Regressão PD-12: banco fora do par Wise/BofA aparece em ``por_banco``
    e a soma da enumeração fecha com ``total_usd``."""
    e5 = {
        "exposicao_cambial": {
            "detalhes": [
                {"fonte": "Wise (extratoconta)", "moeda": "USD", "saldo_original": 500.0},
                {"fonte": "Bankofamerica (extratoconta)", "moeda": "USD", "saldo_original": 2605.0},
                {"fonte": "Avenue (extratoconta)", "moeda": "USD", "saldo_original": 1200.0},
            ]
        }
    }
    out = _compute_usd_saldos_per_bank(e5)
    assert out["por_banco"]["Avenue"] == 1200.0
    assert out["total_usd"] == sum(out["por_banco"].values())


def test_usd_saldos_ignora_nao_usd_e_saldo_invalido():
    e5 = {
        "exposicao_cambial": {
            "detalhes": [
                {"fonte": "Wise", "moeda": "EUR", "saldo_original": 100.0},
                {"fonte": "Bofa", "moeda": "USD", "saldo_original": None},
            ]
        }
    }
    out = _compute_usd_saldos_per_bank(e5)
    assert out["total_usd"] == 0.0
    assert out["por_banco"] == {}


def test_usd_saldos_vazio_sem_exposicao():
    assert _compute_usd_saldos_per_bank({})["total_usd"] == 0.0


def test_fmt_usd_por_banco_enumera_desc_e_inclui_todos():
    texto = _fmt_usd_por_banco({"Wise": 500.0, "Avenue": 1200.0, "Bank of America": 2605.0})
    assert texto == "US$ 2,6k em Bank of America, US$ 1,2k em Avenue, US$ 500 em Wise"


def test_fmt_usd_por_banco_vazio_tem_fallback_sem_bancos_fantasma():
    texto = _fmt_usd_por_banco({})
    assert "Wise" not in texto
    assert "US$" not in texto
    assert texto == "nenhum saldo em moeda estrangeira identificado no período"
