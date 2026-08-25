"""Bases canônicas de denominador do E5 ([[ADR-412]] §D1).

Uma base é o **conjunto de termos** que forma um denominador, não o número.
Publicá-la como enum fechado + termos em dados é o que permite auditar de que
base uma razão saiu **só do payload** — hoje é preciso ler código-fonte para
saber o que entra em "carteira produtiva".
"""

from __future__ import annotations

from enum import Enum


class BaseFinanceira(str, Enum):
    """Denominador canônico; `carteira_com_titular_identificado` é piso derivado."""

    carteira_financeira_familia = "carteira_financeira_familia"
    carteira_produtiva_familia = "carteira_produtiva_familia"
    carteira_com_titular_identificado = "carteira_com_titular_identificado"
    patrimonio_liquido = "patrimonio_liquido"


# Termos em DADOS e não em prosa: a §Precisão da [[A40.l80]] pede que a base de
# cada número seja campo, porque afirmação em prosa envelhece no rebase.
TERMOS_DA_BASE: dict[BaseFinanceira, tuple[str, ...]] = {
    BaseFinanceira.carteira_financeira_familia: (
        "investimentos_titular",
        "investimentos_conjuge",
        "investimentos_nao_atribuidos",
        "caixa_total_brl",
    ),
    BaseFinanceira.carteira_produtiva_familia: (
        "carteira_financeira_familia",
        "cat2_efetivo",
    ),
    BaseFinanceira.carteira_com_titular_identificado: (
        "investimentos_titular",
        "investimentos_conjuge",
        "caixa_total_brl",
    ),
    BaseFinanceira.patrimonio_liquido: ("bruto", "-dividas"),
}

# Amputa a fatia sem titular do denominador: responde "de quanto se sabe o dono"
# sob o rótulo "quanto a família tem" ([[ADR-412]] §D0). Só vale como extremo
# inferior de intervalo declarado — nunca como denominador de número sozinho.
BASES_SO_COMO_EXTREMO_DE_INTERVALO: frozenset[BaseFinanceira] = frozenset(
    {BaseFinanceira.carteira_com_titular_identificado}
)


def termos_da_base(base: BaseFinanceira) -> tuple[str, ...]:
    """Termos que somam a base, na ordem em que o produtor os acumula."""
    return TERMOS_DA_BASE[base]


def publicavel_sozinha(base: BaseFinanceira) -> bool:
    """`False` quando a base só pode aparecer como extremo de um intervalo."""
    return base not in BASES_SO_COMO_EXTREMO_DE_INTERVALO


# `reserva_liquidez.py:62` e `patrimonio_types.inv_key` montam a chave por
# f-string sobre o papel. Com enum isso vira `investimentos_PapelMembro.sem_dono`
# — chave que o `$def` fechado rejeita, e que quebra também titular e cônjuge.
# O mapa explícito é o que impede o PR2 de descobrir isso em produção.
CHAVE_DE_COMPONENTE: dict[str, str] = {
    "titular": "investimentos_titular",
    "conjuge": "investimentos_conjuge",
    "sem_dono": "investimentos_nao_atribuidos",
}


def chave_de_componente(papel: str) -> str:
    """Chave publicada do balde daquele papel, nunca derivada por f-string."""
    return CHAVE_DE_COMPONENTE[papel]
