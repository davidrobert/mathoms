"""Tests — `compute_exposicao_cambial` (Bloco G plan RESIDENCIA_E_USO off-shoot)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.exposicao_cambial_analyzer import (
    THRESHOLD_AMARELO_PCT,
    THRESHOLD_VERDE_PCT,
    compute_exposicao_cambial,
)


def _caixa(moeda: str, valor_brl_raw: int, conta: str = "Wise") -> dict:
    """Boundary: caixa_detalhes vem como dict do payload E5 (valor_brl: float/str)."""
    return {
        "conta": conta,
        "moeda": moeda,
        "saldo_original": valor_brl_raw,
        "valor_brl": valor_brl_raw,
    }


def test_empty_inputs_returns_zero_tier_empty():
    r = compute_exposicao_cambial(
        caixa_detalhes=[], investimentos_atuais=None, investivel_financeiro=0.0
    )
    assert r.total_brl == 0
    assert r.tier == "empty"
    assert r.por_moeda == ()


def test_caixa_usd_e_eur_aggregates_per_moeda():
    r = compute_exposicao_cambial(
        caixa_detalhes=[
            _caixa("USD", 100_000, "Wise"),
            _caixa("USD", 50_000, "BofA"),
            _caixa("EUR", 30_000, "Wise EUR"),
            _caixa("BRL", 200_000, "Itau"),  # ignorado
        ],
        investimentos_atuais=None,
        investivel_financeiro=1_000_000,
    )
    assert r.total_brl == 180_000.0
    assert r.pct_investivel_financeiro == 18.0
    assert r.tier == "verde"  # >=10%
    moedas = {p.moeda: p.valor_brl for p in r.por_moeda}
    assert moedas == {"USD": 150_000.0, "EUR": 30_000.0}


def test_ativos_internacionais_classificados_via_asset_classifier():
    """Ativos com nome `IVVB` ou `Global` viram exposição USD (asset_classifier ADR-193)."""
    r = compute_exposicao_cambial(
        caixa_detalhes=[],
        investimentos_atuais={
            "dados": [
                {"tipo": "ETF Internacional", "descricao": "IVVB ITAU", "valor": 200_000},
                {"tipo": "Fundo", "descricao": "Fundo Global Mundial", "valor": 80_000},
                {"tipo": "Acao", "descricao": "ITSA4", "valor": 50_000},  # Ações BR, não conta
            ]
        },
        investivel_financeiro=1_000_000,
    )
    assert r.total_brl == 280_000.0
    assert round(r.pct_investivel_financeiro, 2) == 28.0
    # Tudo USD (asset_classifier não distingue moeda; assume USD).
    moedas = {p.moeda: p.valor_brl for p in r.por_moeda}
    assert moedas == {"USD": 280_000.0}


def test_caixa_usd_mais_ativo_internacional_agregam_em_usd():
    r = compute_exposicao_cambial(
        caixa_detalhes=[_caixa("USD", 100_000, "Wise")],
        investimentos_atuais={
            "dados": [{"tipo": "ETF", "descricao": "IVVB Internacional", "valor": 50_000}]
        },
        investivel_financeiro=500_000,
    )
    assert r.total_brl == 150_000.0
    assert r.pct_investivel_financeiro == 30.0
    moedas = {p.moeda: p.valor_brl for p in r.por_moeda}
    assert moedas == {"USD": 150_000.0}


def test_tier_thresholds():
    """Verde >=10%; amarelo 5-10%; vermelho <5%."""
    for pct, expected in [(15.0, "verde"), (10.0, "verde"), (7.0, "amarelo"), (3.0, "vermelho")]:
        valor_cambial = pct * 1_000_000 / 100
        r = compute_exposicao_cambial(
            caixa_detalhes=[_caixa("USD", valor_cambial)],
            investimentos_atuais=None,
            investivel_financeiro=1_000_000,
        )
        assert r.tier == expected, f"pct={pct} → expected {expected}, got {r.tier}"


def test_thresholds_constants():
    assert THRESHOLD_VERDE_PCT == 10.0
    assert THRESHOLD_AMARELO_PCT == 5.0


def test_detalhes_inclui_contas_e_ativos():
    r = compute_exposicao_cambial(
        caixa_detalhes=[_caixa("USD", 100_000, "Wise USD")],
        investimentos_atuais={
            "dados": [{"tipo": "ETF Internacional", "descricao": "IVVB", "valor": 50_000}]
        },
        investivel_financeiro=500_000,
    )
    detalhes_caixa = [d for d in r.detalhes if d.get("tipo") == "caixa"]
    detalhes_ativos = [d for d in r.detalhes if d.get("tipo") != "caixa"]
    assert len(detalhes_caixa) == 1
    assert detalhes_caixa[0]["fonte"] == "Wise USD"
    assert len(detalhes_ativos) == 1
    assert detalhes_ativos[0]["moeda"] == "USD"
