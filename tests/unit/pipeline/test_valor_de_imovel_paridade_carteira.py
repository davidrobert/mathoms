"""Classes e ranking valoram imóvel pelo MESMO `imovel_valor` do patrimônio ([[ADR-431]]).

Os dois analyzers tinham cadeia própria (`valor_31_12_ano_base or valor_irpf or valor`):
zero declarado em 31/12 caía no fallback, e valor não apurado era ignorado. Dois
produtores do mesmo estoque lendo fontes diferentes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.investimentos_classes_analyzer import InvestimentosClassesAnalyzer
from pipeline.domain.services.patrimonio_types import imovel_valor
from pipeline.domain.services.top_ativos_analyzer import TopAtivosAnalyzer

LAYOUTS = {
    "vendido_no_ano": {"valor_31_12_ano_base": 0, "valor_irpf": 300_000},
    "nao_apurado": {"valor_nao_apurado": {"anos": ["2025"]}, "valor_irpf": 300_000},
    "declarado": {"valor_31_12_ano_base": 250_000, "valor_irpf": 300_000},
    "so_valor": {"valor": 100_000},
}


def _valor_na_tabela(imovel: dict) -> Decimal:
    r = InvestimentosClassesAnalyzer().analyze([{"imoveis": [imovel]}])
    linhas = [c for c in r.tabela_classes if c.categoria == "Imóveis Investimento"]
    return sum((Decimal(str(c.valor)) for c in linhas), Decimal("0"))


def _valor_no_ranking(imovel: dict) -> Decimal:
    r = TopAtivosAnalyzer().analyze([("Alex", {"imoveis": [imovel]})])
    return sum((a.valor for a in r.top_ativos if a.tipo_origem == "imovel"), Decimal("0"))


@pytest.mark.parametrize("layout", LAYOUTS, ids=str)
def test_tabela_de_classes_valora_como_o_patrimonio(layout: str) -> None:
    imovel = LAYOUTS[layout]
    assert _valor_na_tabela(imovel) == Decimal(str(imovel_valor(imovel)))


@pytest.mark.parametrize("layout", LAYOUTS, ids=str)
def test_ranking_valora_como_o_patrimonio(layout: str) -> None:
    imovel = LAYOUTS[layout]
    assert _valor_no_ranking(imovel) == Decimal(str(imovel_valor(imovel)))
