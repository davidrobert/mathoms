"""Bases canônicas de denominador do E5 ([[ADR-412]] §D1).

Uma base é o **conjunto de termos** que forma um denominador, não o número.
Publicá-la como enum fechado + termos em dados é o que permite auditar de que
base uma razão saiu **só do payload** — hoje é preciso ler código-fonte para
saber o que entra em "carteira produtiva".
"""

from __future__ import annotations

from enum import Enum
from typing import Mapping


# `sem_dono` existe porque o domínio é ternário e `role_of` é binária: o `else`
# dela devolve `titular` para chave que não casa ninguém, afirmando posse que
# ninguém mediu. O enum sozinho NÃO trava a omissão do terceiro caso — não há
# mypy nem pyright em gate, e o mixin `str` mantém `PapelMembro.titular ==
# "titular"` verdadeiro, então um if/else binário segue calado. Quem trava é o
# teste de exaustividade sobre `set(PapelMembro)`, que o PR2 traz.
class PapelMembro(str, Enum):
    """Papel de uma posição — ternário ([[ADR-412]] §D2)."""

    titular = "titular"
    conjuge = "conjuge"
    sem_dono = "sem_dono"


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
# Chaveado pelo MEMBRO do enum, não pela string: `str, Enum` faz o hash colidir
# com o valor hoje, e a igualdade sobreviveria a um rename de valor sem avisar.
CHAVE_DE_COMPONENTE: dict[PapelMembro, str] = {
    PapelMembro.titular: "investimentos_titular",
    PapelMembro.conjuge: "investimentos_conjuge",
    PapelMembro.sem_dono: "investimentos_nao_atribuidos",
}


def chave_de_componente(papel: PapelMembro) -> str:
    """Chave publicada do balde daquele papel, nunca derivada por f-string."""
    return CHAVE_DE_COMPONENTE[papel]


# Fronteira de série ([[ADR-412]] §D8): superfície read-time que recompõe artefato
# antigo com código novo produziria híbrido sem rótulo. Ausência do campo é "não
# sei", nunca "série corrente".
BASE_VERSAO_CORRENTE = 1


# Recebe valores CRUS, nunca o dict publicado: lá `valor_publicavel` já pode ter
# virado `None` para membro não apurado, e a base sairia menor que o número que
# ela diz explicar.
def publicar_bases(
    *,
    titular: float,
    conjuge: float,
    sem_dono: float,
    caixa: float,
    carteira_financeira: float,
    cat2_efetivo: float,
    bruto: float,
    dividas: float,
) -> dict[str, dict]:
    """Bloco `bases` + `base_versao` a partir dos valores crus; `-` subtrai."""
    valores = {
        "investimentos_titular": titular,
        "investimentos_conjuge": conjuge,
        "investimentos_nao_atribuidos": sem_dono,
        "caixa_total_brl": caixa,
        "carteira_financeira_familia": carteira_financeira,
        "cat2_efetivo": cat2_efetivo,
        "bruto": bruto,
        "dividas": dividas,
    }
    return {
        "bases": {
            base.value: {
                "termos": list(termos_da_base(base)),
                "valor_brl": round(_somar_termos(termos_da_base(base), valores), 2),
            }
            for base in BaseFinanceira
        },
        "base_versao": BASE_VERSAO_CORRENTE,
    }


def _somar_termos(termos: tuple[str, ...], valores: Mapping[str, float]) -> float:
    total = 0.0
    for termo in termos:
        negativo = termo.startswith("-")
        nome = termo[1:] if negativo else termo
        valor = float(valores.get(nome) or 0.0)
        total += -valor if negativo else valor
    return total
