"""Tests — `compute_exposicao_cambial` (Bloco G plan RESIDENCIA_E_USO off-shoot)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.exposicao_cambial_analyzer import (
    THRESHOLD_AMARELO_PCT,
    THRESHOLD_VERDE_PCT,
    _tier_from_pct,
    compute_exposicao_cambial,
)


def _carteira(r) -> Decimal:
    return r.componentes["carteira_lastro_estrangeiro"].valor_brl


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
    # Pós-ADR-403 a cobertura da carteira é indeterminada e tem precedência
    # sobre `empty` — sem posições medidas, "sem exposição" seria afirmação.
    assert r.tier == "indeterminado"
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
    # O piso medido (18%) continua publicado; o VEREDITO é suprimido enquanto
    # o componente de carteira não for apurado (ADR-403).
    assert _tier_from_pct(r.pct_investivel_financeiro, has_data=True) == "verde"
    assert r.tier == "indeterminado"
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
    # v1 (ADR-403): a carteira é OBSERVACIONAL — medida e publicada com a
    # própria cobertura, fora de `total_brl`, que só soma o que foi apurado.
    assert _carteira(r) == 280_000.0
    assert r.total_brl == 0
    assert r.componentes["carteira_lastro_estrangeiro"].cobertura.value == "indeterminado"


def test_caixa_usd_mais_ativo_internacional_agregam_em_usd():
    r = compute_exposicao_cambial(
        caixa_detalhes=[_caixa("USD", 100_000, "Wise")],
        investimentos_atuais={
            "dados": [{"tipo": "ETF", "descricao": "IVVB Internacional", "valor": 50_000}]
        },
        investivel_financeiro=500_000,
    )
    # Era `..._agregam_em_usd`: os dois DEIXAM de se fundir num escalar único
    # (ADR-403). Cada componente carrega o próprio valor e a própria cobertura,
    # e só o apurado entra no total — somar às cegas inflava o KPI.
    assert r.total_brl == 100_000.0
    assert _carteira(r) == 50_000.0
    moedas = {p.moeda: p.valor_brl for p in r.por_moeda}
    assert moedas == {"USD": 100_000.0}


# A banda continua a mesma (decisão do dono 2026-08-19: separar os objetos e
# rotular, não recalibrar). O que a ADR-403 muda é QUANDO ela é aplicável.
def test_tier_thresholds():
    """Verde >=10%; amarelo 5-10%; vermelho <5% — a BANDA, não o veredito."""
    for pct, expected in [(15.0, "verde"), (10.0, "verde"), (7.0, "amarelo"), (3.0, "vermelho")]:
        assert _tier_from_pct(pct, has_data=True) == expected, f"pct={pct}"


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


def test_irpf_me_entra_mesmo_com_moeda_brl():
    """ADR-390: fallback IRPF (moeda=BRL, tipo=moeda_estrangeira_irpf) conta."""
    r = compute_exposicao_cambial(
        caixa_detalhes=[
            {
                "conta": "IRPF: DEPOSITO EM MOEDA ESTRANGEIRA DOLAR",
                "moeda": "BRL",
                "saldo_original": 25_000,
                "valor_brl": 25_000,
                "tipo": "moeda_estrangeira_irpf",
            }
        ],
        investimentos_atuais=None,
        investivel_financeiro=250_000,
    )
    assert r.total_brl == 25_000
    moedas = {p.moeda: p.valor_brl for p in r.por_moeda}
    assert moedas == {"USD": 25_000}


def test_rv2_08_ativo_le_valor_atual_nao_zero():
    """RV2-08: posição E4 usa `valor_atual` (não `valor`) — antes lia 0 e o ativo sumia."""
    r = compute_exposicao_cambial(
        caixa_detalhes=[],
        investimentos_atuais={
            "dados": [
                {
                    "tipo": "etf",
                    "nome": "Wise USD balance",
                    "instituicao": "Wise",
                    "valor_atual": "5000",
                }
            ]
        },
        investivel_financeiro=10_000,
    )
    # A posição continua LIDA por `valor_atual` (o bug RV2-08 fazia ler 0), mas
    # cai no componente de carteira, não no total de v1.
    assert _carteira(r) == Decimal("5000")
    assert any(d.get("moeda") == "USD" for d in r.detalhes)
