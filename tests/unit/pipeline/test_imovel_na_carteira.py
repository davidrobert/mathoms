"""Roteamento único do imóvel na carteira e o conjunto único de classes de imóvel físico.

Classe de imóvel que fique fora de `CLASSES_IMOVEL_FISICO` some calada de um leitor: a
alocação descarta categoria que não reconhece, e o peso sobre a carteira financeira
passaria a contá-la como ativo financeiro.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from pipeline.domain.services.alocacao_alvo_deviation import AlocacaoAlvoDeviationCalculator
from pipeline.domain.services.imovel_na_carteira import (
    CLASSE_IMOVEIS_INVESTIMENTO,
    CLASSES_IMOVEL_FISICO,
    CLASSES_SEM_PESO,
    classe_do_imovel_na_carteira,
)
from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesAnalyzer,
    InvestimentosClassesConfig,
    _pct_carteira_financeira,
)
from pipeline.domain.services.patrimonio_imovel_classifier import (
    CLASSIFICATION_COMERCIAL,
    CLASSIFICATION_DESCONHECIDO,
    CLASSIFICATION_ESPECULACAO,
    CLASSIFICATION_LOCADO,
    CLASSIFICATION_NU_PROPRIETARIO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATION_USO_PESSOAL,
    CLASSIFICATIONS_FORA_DA_ALOCACAO,
)
from pipeline.domain.services.top_ativos_analyzer import TopAtivosAnalyzer, TopAtivosConfig

_SCHEMA_E5 = Path(__file__).resolve().parents[3] / "config" / "schemas" / "e5_analysis.schema.json"


def _categorias_do_schema() -> list[str]:
    investimentos = json.loads(_SCHEMA_E5.read_text(encoding="utf-8"))["properties"][
        "investimentos"
    ]
    return investimentos["properties"]["tabela_classes"]["items"]["properties"]["categoria"]["enum"]


_OVERRIDES = {
    "p-casa": "residencia_principal",
    "p-sala": "locado",
    "p-praia": "uso_pessoal",
    "p-nua": "nu_proprietario",
    "p-terreno": "especulacao",
}
_CASA = {"property_id": "p-casa", "valor_31_12_ano_base": 800_000}
_SALA = {"property_id": "p-sala", "valor_31_12_ano_base": 300_000}
_PRAIA = {"property_id": "p-praia", "valor_31_12_ano_base": 350_000}
_NUA = {"property_id": "p-nua", "valor_31_12_ano_base": 250_000}
_TERRENO = {"property_id": "p-terreno", "valor_31_12_ano_base": 150_000}
_SEM_ID = {"valor_31_12_ano_base": 200_000}
_ID_SEM_OVERRIDE = {"property_id": "p-x", "valor_31_12_ano_base": 100_000}


@pytest.mark.parametrize(
    ("imovel", "esperado"),
    [
        (_CASA, None),
        (_PRAIA, None),
        (_NUA, None),
        (_SALA, CLASSE_IMOVEIS_INVESTIMENTO),
        (_TERRENO, CLASSE_IMOVEIS_INVESTIMENTO),
        (_SEM_ID, CLASSE_IMOVEIS_INVESTIMENTO),
        (_ID_SEM_OVERRIDE, CLASSE_IMOVEIS_INVESTIMENTO),
    ],
    ids=[
        "residencia",
        "uso_pessoal",
        "nu_proprietario",
        "locado",
        "especulacao",
        "sem_id",
        "id_sem_override",
    ],
)
def test_roteamento_do_imovel(imovel: dict, esperado: str | None) -> None:
    assert classe_do_imovel_na_carteira(imovel, _OVERRIDES) == esperado


# [[ADR-444]] D9: a carteira e o numerador da concentração ([[ADR-420]] §D1) cortam pela
# MESMA lista. Editar uma das duas sem a outra reprova aqui, não no relatório.
@pytest.mark.parametrize(
    "classificacao",
    [
        CLASSIFICATION_RESIDENCIA_PRINCIPAL,
        CLASSIFICATION_USO_PESSOAL,
        CLASSIFICATION_NU_PROPRIETARIO,
        CLASSIFICATION_LOCADO,
        CLASSIFICATION_COMERCIAL,
        CLASSIFICATION_ESPECULACAO,
    ],
)
def test_fora_da_carteira_e_a_lista_da_concentracao(classificacao: str) -> None:
    imovel = {"property_id": "p-1", "valor_31_12_ano_base": 100_000}
    fora = classe_do_imovel_na_carteira(imovel, {"p-1": classificacao}) is None
    esperado = classificacao in CLASSIFICATIONS_FORA_DA_ALOCACAO | {
        CLASSIFICATION_RESIDENCIA_PRINCIPAL
    }
    assert fora is esperado


def test_desconhecido_segue_na_carteira() -> None:
    """Sem classificação não há declaração de uso: o lado conservador ([[ADR-420]] §D2)."""
    imovel = {"valor_31_12_ano_base": 100_000}
    assert classe_do_imovel_na_carteira(imovel, {}) == CLASSE_IMOVEIS_INVESTIMENTO
    assert CLASSIFICATION_DESCONHECIDO not in CLASSIFICATIONS_FORA_DA_ALOCACAO


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
    assert _pct_carteira_financeira(classe, 500_000.0, 100_000.0) is None


def test_classe_financeira_tem_peso_na_carteira_financeira() -> None:
    assert _pct_carteira_financeira("Renda Fixa", 50_000.0, 100_000.0) == 50.0


def test_classe_sem_peso_e_classe_fisica() -> None:
    assert CLASSES_SEM_PESO <= CLASSES_IMOVEL_FISICO


# Exaustividade sobre o CONTRATO, não sobre a lista do módulo: categoria que o schema aceita
# e a alocação não reconhece seria descartada calada e moveria o caixa% (ADR-444 D7).
@pytest.mark.parametrize("categoria", _categorias_do_schema())
def test_alocacao_ingere_toda_categoria_do_schema(categoria: str) -> None:
    resultado = AlocacaoAlvoDeviationCalculator().calculate(
        [{"categoria": categoria, "valor": 100}]
    )
    ingerido = (
        resultado.carteira_liquida_brl + resultado.caixa.valor_brl + resultado.imoveis_fisicos_brl
    )
    assert ingerido == Decimal("100")


@pytest.mark.parametrize("classe", sorted(CLASSES_IMOVEL_FISICO))
def test_alocacao_ingere_toda_classe_fisica_como_imovel(classe: str) -> None:
    tabela = [{"categoria": classe, "valor": 500_000}, {"categoria": "Caixa", "valor": 100_000}]
    resultado = AlocacaoAlvoDeviationCalculator().calculate(tabela, {"caixa_pct": 5.0})
    assert resultado.imoveis_fisicos_brl == Decimal("500000")
    assert resultado.caixa.atual_pct_patrimonio == pytest.approx(100_000 / 600_000 * 100)
