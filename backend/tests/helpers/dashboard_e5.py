"""E5 sintético do dashboard, montado pelos produtores reais do E5 — nunca à mão.

Compartilhado pelos testes de gráfico (par com a fixture do frontend) e de KPI. Valores
sintéticos; 14 meses para que a janela de 12 do gráfico mensal corte alguma coisa.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pipeline.domain.services.fluxo_caixa_enricher import FluxoCaixaEnricher
from pipeline.domain.services.investimentos_cobertura import CoberturaStatus
from pipeline.domain.services.patrimonio_composicao import build_composicao
from pipeline.domain.services.patrimonio_types import MemberIdentity
from pipeline.domain.services.ratios_calculator import RatiosCalculator
from pipeline.domain.services.veredito_balde_imovel import MotivoBaldeImovel, VereditoBalde

MESES = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01", "2026-02"]
RECEITA_MES = 20000.0
CONSUMO_MES = 9000.0
APORTE_MES = 4000.0


def _por_mes(**valores: float) -> dict[str, dict[str, float]]:
    return {mes: {**valores, "_total": sum(valores.values())} for mes in MESES}


def _fluxo_caixa() -> dict[str, Any]:
    n = len(MESES)
    receitas = {
        "total_geral": RECEITA_MES * n,
        "totais_por_categoria": {"receita_clt": RECEITA_MES * n},
    }
    despesas = {
        "total_geral": (CONSUMO_MES + APORTE_MES) * n,
        "totais_por_categoria": {
            "alimentacao": CONSUMO_MES * n,
            "aporte_investimento": APORTE_MES * n,
        },
    }
    fluxo_mensal = {
        "meses_ordenados": MESES,
        "receitas": {"por_mes": _por_mes(receita_clt=RECEITA_MES)},
        "despesas": {"por_mes": _por_mes(alimentacao=CONSUMO_MES, aporte_investimento=APORTE_MES)},
    }
    enriched = FluxoCaixaEnricher().enrich(
        receitas, despesas, fluxo_mensal, data_corte=date(2026, 2, 28)
    )
    return enriched.to_legacy_dict()


# ADR-439 D5: residência não apurada fica `valor: 0` com `estado`/`motivo`; veículos 0 sem
# estado é o zero comum — os dois saem da pizza por razões diferentes.
def _composicao() -> list[dict[str, Any]]:
    return build_composicao(
        identity=MemberIdentity("titular", "conjuge", "Titular", "Cônjuge"),
        residencia=0.0,
        imoveis_investimento=200000.0,
        investimentos_titular=300000.0,
        investimentos_conjuge=100000.0,
        caixa=50000.0,
        veiculos=0.0,
        veredito_residencia=VereditoBalde(
            CoberturaStatus.nao_apurado, MotivoBaldeImovel.nao_classificada
        ),
    )


# `tabela_classes` segue à mão, como no par original (#2087): o último item antecipa a
# A40.l122 — imóvel com uso não apurado publica `pct` null, e o gráfico plota `valor`.
_INVESTIMENTOS = {
    "tabela_classes": [
        {
            "categoria": "Renda Fixa",
            "valor": 300000.0,
            "pct": 40.0,
            "pct_carteira_financeira": 75.0,
        },
        {
            "categoria": "Imóveis Investimento",
            "valor": 200000.0,
            "pct": 26.67,
            "pct_carteira_financeira": None,
        },
        {"categoria": "Ações BR", "valor": 100000.0, "pct": 13.33, "pct_carteira_financeira": 25.0},
        {
            "categoria": "Imóveis com uso não apurado",
            "valor": 150000.0,
            "pct": None,
            "pct_carteira_financeira": None,
        },
    ],
    "total": 750000.0,
}


def e5_sintetico() -> dict[str, Any]:
    fluxo = _fluxo_caixa()
    patrimonio = {"composicao": _composicao()}
    return {
        "fluxo_caixa": fluxo,
        "patrimonio": patrimonio,
        "ratios": RatiosCalculator().calculate(fluxo, patrimonio).to_legacy_dict(),
        "score": {"valor": 72, "max": 100},
        "investimentos": _INVESTIMENTOS,
    }
