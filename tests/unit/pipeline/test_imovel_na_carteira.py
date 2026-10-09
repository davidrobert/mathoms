"""Roteamento único do imóvel na carteira e o conjunto único de classes de imóvel físico.

Classe de imóvel que fique fora de `CLASSES_IMOVEL_FISICO` some calada de um leitor: a
alocação descarta categoria que não reconhece, e o peso sobre a carteira financeira
passaria a contá-la como ativo financeiro.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.alocacao_alvo_deviation import AlocacaoAlvoDeviationCalculator
from pipeline.domain.services.imovel_na_carteira import (
    CLASSE_IMOVEIS_INVESTIMENTO,
    CLASSES_IMOVEL_FISICO,
    classe_do_imovel_na_carteira,
)
from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesAnalyzer,
    InvestimentosClassesConfig,
)
from pipeline.domain.services.top_ativos_analyzer import TopAtivosAnalyzer, TopAtivosConfig

_OVERRIDES = {"p-casa": "residencia_principal", "p-sala": "locado"}
_CASA = {"property_id": "p-casa", "valor_31_12_ano_base": 800_000}
_SALA = {"property_id": "p-sala", "valor_31_12_ano_base": 300_000}
_SEM_ID = {"valor_31_12_ano_base": 200_000}
_ID_SEM_OVERRIDE = {"property_id": "p-x", "valor_31_12_ano_base": 100_000}


@pytest.mark.parametrize(
    ("imovel", "esperado"),
    [
        (_CASA, None),
        (_SALA, CLASSE_IMOVEIS_INVESTIMENTO),
        (_SEM_ID, CLASSE_IMOVEIS_INVESTIMENTO),
        (_ID_SEM_OVERRIDE, CLASSE_IMOVEIS_INVESTIMENTO),
    ],
    ids=["residencia", "locado", "sem_id", "id_sem_override"],
)
def test_roteamento_do_imovel(imovel: dict, esperado: str | None) -> None:
    assert classe_do_imovel_na_carteira(imovel, _OVERRIDES) == esperado


def test_tabela_e_ranking_roteiam_pelo_mesmo_classificador() -> None:
    imoveis = [_CASA, _SALA, _SEM_ID, _ID_SEM_OVERRIDE]
    classes = InvestimentosClassesAnalyzer(
        InvestimentosClassesConfig.from_configs(property_classification_overrides=_OVERRIDES)
    ).analyze([{"imoveis": imoveis}])
    top = TopAtivosAnalyzer(
        TopAtivosConfig.from_configs(property_classification_overrides=_OVERRIDES)
    ).analyze([("Alex", {"imoveis": imoveis})])

    na_tabela = {c.categoria: Decimal(str(c.valor)) for c in classes.tabela_classes}
    no_ranking = sum((a.valor for a in top.top_ativos), Decimal("0"))
    assert na_tabela == {CLASSE_IMOVEIS_INVESTIMENTO: Decimal("600000")}
    assert no_ranking == Decimal("600000")


@pytest.mark.parametrize("classe", sorted(CLASSES_IMOVEL_FISICO))
def test_classe_fisica_fica_fora_da_carteira_financeira(classe: str) -> None:
    analise = InvestimentosClassesAnalyzer().analyze(
        [{"imoveis": [_SEM_ID], "investimentos": [{"tipo": "CDB", "valor": 100_000}]}]
    )
    linha = next(c for c in analise.tabela_classes if c.categoria == classe)
    assert linha.pct_carteira_financeira is None
    assert analise.total_financeiro == Decimal("100000.0")


@pytest.mark.parametrize("classe", sorted(CLASSES_IMOVEL_FISICO))
def test_alocacao_ingere_toda_classe_fisica_como_imovel(classe: str) -> None:
    tabela = [{"categoria": classe, "valor": 500_000}, {"categoria": "Caixa", "valor": 100_000}]
    resultado = AlocacaoAlvoDeviationCalculator().calculate(tabela, {"caixa_pct": 5.0})
    assert resultado.imoveis_fisicos_brl == Decimal("500000")
    assert resultado.caixa.atual_pct_patrimonio == pytest.approx(100_000 / 600_000 * 100)
