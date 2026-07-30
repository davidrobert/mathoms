"""Fixture builders compartilhados pelos testes do detector cross-grupo ([[ADR-354]])."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# As 8 chaves que ``to_legacy_dict`` emite em despesa/receita — sem ``tipo`` (só
# transferência serializa, e transferência não vai a balde): inventá-lo faria o
# caso (b) do critério de aceite passar pelo motivo errado.
TX_BASE: dict = {
    "data": "2026-03-30",
    "descricao": "compra mercado",
    "valor": 100.0,
    "banco": "banco exemplo",
    "tipo_conta": "extratoconta",
    "titular": "",
    "moeda": "BRL",
    "categoria": "outros",
}


def tx(**overrides) -> dict:
    """Item de balde transacional; ``overrides`` troca campo a campo do shape real."""
    assert not set(overrides) - set(TX_BASE), "campo fora do shape do item E4"
    return {**TX_BASE, **overrides}


def bucket(rows: list) -> dict:
    return {
        "dados": {"outros": rows},
        "total_geral": 0.0,
        "totais_por_categoria": {},
        "total_transacoes": len(rows),
    }


def buckets(*, despesas=(), receitas=()) -> dict:
    """Payload E4 no shape de produção: ``dados`` é DICT de listas por categoria."""
    return {"despesas": bucket(list(despesas)), "receitas": bucket(list(receitas))}


def par_divergente(**kwargs) -> dict:
    """Duas pernas com ``tipo_conta`` divergente — proveniência distinta de propósito."""
    return buckets(
        despesas=[tx(tipo_conta="extrato", **kwargs), tx(tipo_conta="extratoconta", **kwargs)]
    )


def carrier_adr354() -> dict:
    """Fixture FIXA do carrier: ``tipo_conta`` variante e ``titular`` ASSIMÉTRICO."""
    return buckets(
        despesas=[
            tx(tipo_conta="extrato", titular=""),
            tx(tipo_conta="extratoconta", titular="titular exemplo"),
        ]
    )


def coincidencia_cross_conta() -> dict:
    """Sobre-detecção DECLARADA: contas genuinamente distintas, pernas simétricas."""
    return buckets(
        despesas=[
            tx(banco="banco a", titular="membro um"),
            tx(banco="banco b", titular="membro dois"),
        ]
    )


def duas_ocorrencias_uma_imaterial() -> dict:
    """Uma ocorrência material e uma de 1 centavo — qualquer piso ou cap dentro do
    numerador derruba a segunda, e é isso que dá dente à 3ª identidade."""
    return buckets(
        despesas=[
            tx(tipo_conta="extrato", valor=100.0),
            tx(tipo_conta="extratoconta", valor=100.0),
            tx(tipo_conta="extrato", valor=0.01, descricao="tarifa"),
            tx(tipo_conta="extratoconta", valor=0.01, descricao="tarifa"),
        ]
    )
