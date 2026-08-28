"""Bases canônicas de denominador do E5 ([[ADR-412]] §D1).

Uma base é o **conjunto de termos** que forma um denominador, não o número.
Publicá-la como enum fechado + termos em dados é o que permite auditar de que
base uma razão saiu **só do payload** — hoje é preciso ler código-fonte para
saber o que entra em "carteira produtiva".
"""

from __future__ import annotations

from decimal import Decimal
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
    carteira_produtiva_com_titular_identificado = "carteira_produtiva_com_titular_identificado"
    carteira_produtiva_fixa = "carteira_produtiva_fixa"
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
    # O bloco IF consome `investivel_efetivo` = carteira financeira + cat_2. Sem
    # esta base o extremo conservador do IF sairia com base NÃO declarada, ou
    # remontada dos termos sem citar o nome — a terceira fuga que a própria
    # §Consequências da [[ADR-412]] nomeia.
    BaseFinanceira.carteira_produtiva_com_titular_identificado: (
        "carteira_com_titular_identificado",
        "cat2_efetivo",
    ),
    # A base da concentração imobiliária ([[ADR-340]]) NÃO é a `carteira_produtiva_familia`:
    # aquela soma `cat2_efetivo` (só imóveis GERADORES, e zero quando o toggle
    # `include_real_estate_in_if` está off), enquanto a concentração divide por cat_2
    # COMPLETO e é toggle-independente por decisão — o docstring de
    # `concentracao_imobiliaria.py` diz "FIXA/toggle-independente", e vago/especulação
    # entra porque é ainda mais ilíquido. Medido no dogfood: 73.000.000 contra
    # 13.000.000 da homônima, 5,6× — dois denominadores sob o mesmo nome "carteira
    # produtiva", que é o defeito RV8-02 um nível acima. Declará-la é número-neutro.
    BaseFinanceira.carteira_produtiva_fixa: (
        "carteira_financeira_familia",
        "imoveis_investimento",
    ),
    BaseFinanceira.patrimonio_liquido: ("bruto", "-dividas"),
}

# Amputa a fatia sem titular do denominador: responde "de quanto se sabe o dono"
# sob o rótulo "quanto a família tem" ([[ADR-412]] §D0). Só vale como extremo
# inferior de intervalo declarado — nunca como denominador de número sozinho.
BASES_SO_COMO_EXTREMO_DE_INTERVALO: frozenset[BaseFinanceira] = frozenset(
    {
        BaseFinanceira.carteira_com_titular_identificado,
        BaseFinanceira.carteira_produtiva_com_titular_identificado,
    }
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
def publicar_bases(valores_crus: Mapping[str, float]) -> dict[str, dict]:
    """Bloco `bases` + `base_versao`; prefixo `-` no termo subtrai."""
    return {
        "bases": {base.value: _base_declarada(base, valores_crus) for base in BaseFinanceira},
        "base_versao": BASE_VERSAO_CORRENTE,
    }


def _base_declarada(base: BaseFinanceira, valores: Mapping[str, float]) -> dict:
    return {
        "termos": list(termos_da_base(base)),
        "valor_brl": float(round(_valor_da_base(base, valores), 2)),
    }


# Termo pode nomear OUTRA base (`carteira_produtiva_familia` = carteira financeira
# + cat_2). Sem resolver a referência, a base derivada sai ZERO quando o chamador
# não pré-computou a intermediária — foi assim que
# `carteira_produtiva_com_titular_identificado` saiu 0 no primeiro dogfood.
def _valor_da_base(base: BaseFinanceira, valores: Mapping[str, float]) -> Decimal:
    total = Decimal("0")
    for termo in termos_da_base(base):
        negativo = termo.startswith("-")
        nome = termo[1:] if negativo else termo
        vizinha = next((b for b in BaseFinanceira if b.value == nome), None)
        valor = (
            _valor_da_base(vizinha, valores) if vizinha else Decimal(str(valores.get(nome) or 0.0))
        )
        total += -valor if negativo else valor
    return total
