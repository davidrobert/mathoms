"""Contrato da linha "Imóveis com uso não apurado" ([[ADR-444]] D7): `null` discriminado.

`pct` (tabela) e `pct_carteira` (ranking) só podem ser `null` na linha nova — com valor e sem
peso. Alargar o tipo das dez classes cegaria o modo `strict`: linha financeira sem
percentual passaria calada.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from pipeline.domain.services.imovel_na_carteira import CLASSE_IMOVEIS_USO_NAO_APURADO

_SCHEMA = Path(__file__).resolve().parents[3] / "config" / "schemas" / "e5_analysis.schema.json"
_INVESTIMENTOS = json.loads(_SCHEMA.read_text(encoding="utf-8"))["properties"]["investimentos"]
_LINHA = _INVESTIMENTOS["properties"]["tabela_classes"]["items"]
_ITEM = _INVESTIMENTOS["properties"]["top_ativos"]["items"]
_ITEM_BASE = {
    "posicao": 1,
    "nome": "Imóvel com uso não apurado",
    "membro": "Alex",
    "instituicao": "",
    "valor": 1.0,
    "tipo_origem": "imovel",
}


def _valido(schema: dict, instancia: dict) -> bool:
    return jsonschema.Draft202012Validator(schema).is_valid(instancia)


@pytest.mark.parametrize(
    ("categoria", "pct", "esperado"),
    [
        (CLASSE_IMOVEIS_USO_NAO_APURADO, None, True),
        (CLASSE_IMOVEIS_USO_NAO_APURADO, 12.0, False),
        ("Renda Fixa", None, False),
        ("Imóveis Investimento", None, False),
        ("Renda Fixa", 10.0, True),
    ],
)
def test_pct_da_tabela_so_e_null_na_linha_sem_peso(categoria, pct, esperado) -> None:
    linha = {"categoria": categoria, "valor": 100.0, "pct": pct, "pct_carteira_financeira": None}
    assert _valido(_LINHA, linha) is esperado


@pytest.mark.parametrize(
    ("classe", "pct", "esperado"),
    [
        (CLASSE_IMOVEIS_USO_NAO_APURADO, None, True),
        (CLASSE_IMOVEIS_USO_NAO_APURADO, 3.0, False),
        ("Imóveis Investimento", None, False),
        ("Imóveis Investimento", 3.0, True),
    ],
)
def test_pct_do_ranking_so_e_null_no_item_sem_peso(classe, pct, esperado) -> None:
    assert _valido(_ITEM, {**_ITEM_BASE, "classe": classe, "pct_carteira": pct}) is esperado


def test_residencia_nunca_aparece_como_classificacao_no_ranking() -> None:
    item = {**_ITEM_BASE, "classe": "Imóveis Investimento", "pct_carteira": 3.0}
    assert not _valido(_ITEM, {**item, "classificacao_imovel": "residencia_principal"})
    assert _valido(_ITEM, {**item, "classificacao_imovel": "desconhecido"})


def test_linha_sem_peso_e_a_mesma_string_do_produtor() -> None:
    enum = _LINHA["properties"]["categoria"]["enum"]
    assert CLASSE_IMOVEIS_USO_NAO_APURADO in enum
    assert CLASSE_IMOVEIS_USO_NAO_APURADO in _ITEM["properties"]["classe"]["enum"]
