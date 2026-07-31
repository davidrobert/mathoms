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


def bucket_multi(cats: dict) -> dict:
    """Balde com ``dados`` em MAIS DE UMA categoria — a forma real do E4
    (``cash_flow_builder`` agrupa por categoria). Fixture de categoria única deixa
    passar varredura que lê só a primeira."""
    rows = [r for group in cats.values() for r in group]
    return {
        "dados": {cat: list(group) for cat, group in cats.items()},
        "total_geral": 0.0,
        "totais_por_categoria": {},
        "total_transacoes": len(rows),
    }


def bucket(rows: list) -> dict:
    return bucket_multi({"outros": rows})


def buckets(*, despesas=(), receitas=()) -> dict:
    """Payload E4 no shape de produção: ``dados`` é DICT de listas por categoria."""
    return {"despesas": bucket(list(despesas)), "receitas": bucket(list(receitas))}


def par_divergente(**kwargs) -> dict:
    """Duas pernas com ``tipo_conta`` divergente — proveniência distinta de propósito."""
    return buckets(
        despesas=[tx(tipo_conta="extrato", **kwargs), tx(tipo_conta="extratoconta", **kwargs)]
    )


def carrier_1_vocabulario() -> dict:
    """Carrier 1 SOZINHO ([[ADR-354]] §Contexto): ``tipo_conta`` de vocabulário variante com
    ``titular`` SIMÉTRICO — nenhum campo parcial, e ainda assim é carrier."""
    return buckets(
        despesas=[
            tx(tipo_conta="extrato", titular="titular exemplo"),
            tx(tipo_conta="extratoconta", titular="titular exemplo"),
        ]
    )


def _par(**kwargs) -> list:
    """Duas pernas do MESMO evento em ``tipo_conta`` variante (carrier 1)."""
    return [tx(tipo_conta="extrato", **kwargs), tx(tipo_conta="extratoconta", **kwargs)]


def corpus_multi_eixo() -> dict:
    """5 colisões nos DOIS baldes, em 5 categorias e 2 moedas — qualquer filtro de balde,
    de categoria, de ``direction`` ou de moeda derruba o numerador."""
    return {
        "despesas": bucket_multi(
            {
                "moradia": _par(descricao="aluguel", valor=100.0, categoria="moradia"),
                "outros": _par(descricao="compra mercado", valor=250.0),
                "viagem": _par(descricao="hotel", valor=80.0, moeda="USD", categoria="viagem"),
            }
        ),
        "receitas": bucket_multi(
            {
                "salario": _par(descricao="salario", valor=500.0, categoria="salario"),
                "rendimento": _par(
                    descricao="juros", valor=40.0, moeda="USD", categoria="rendimento"
                ),
            }
        ),
    }


def corpus_denso(n: int) -> dict:
    """``n`` colisões distintas (2 rows cada) — fecha cap CONSTANTE dentro do numerador:
    com a fixture mais densa em 5 colisões, ``[:100]`` passava a suíte inteira verde."""
    rows = [r for i in range(n) for r in _par(descricao=f"compra {i:04d}", valor=10.0 + i)]
    return buckets(despesas=rows)


def carrier_e_coincidencia() -> dict:
    """Corpus MISTO — 1 ocorrência carrier-shaped (Σ 10000 cents) + 1 coincidence-shaped
    (Σ 20000): sem as duas classes, filtrar o número IMPRESSO por ``defect_shaped`` é
    indistinguível de não filtrar."""
    return buckets(
        despesas=[
            *_par(descricao="aluguel", valor=100.0),
            tx(descricao="tarifa", valor=200.0, banco="banco a", titular="membro um"),
            tx(descricao="tarifa", valor=200.0, banco="banco b", titular="membro dois"),
        ]
    )


def par_sem_descricao() -> dict:
    """Par colidente com descrição VAZIA — a classe que uma rota alternativa de whitelist
    (``or not descricao``) mandaria para ``explicadas`` sem tocar na whitelist declarada."""
    return buckets(despesas=_par(descricao=""))


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
