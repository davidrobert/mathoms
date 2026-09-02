"""Produtor único do saldo devedor de uma linha de dívida ([[A40.l114]]).

``saldo_31_12`` é objeto por ano-base ([[ADR-301]]). Antes desta lane havia **dois**
leitores do mesmo campo com semânticas divergentes, e cada um alimentava uma
superfície diferente do relatório:

- ``endividamento_analyzer._resolve_saldo`` caía para ``anos[-1]`` quando o ano-base
  faltava — a **lista de itens** somava certo;
- ``patrimonio_resolvers._split_dividas`` fazia ``saldo.get(ano_ref, 0)`` — o
  **total** saía zero.

Medido no run ``40d1af2a``: ``endividamento.total_dividas`` publicou ``0,00`` na
mesma página em que os quatro financiamentos somavam ``R$ 230.459,13``.

A regra é a Rota C decidida pelo `financial-planner` em 2026-09-01: **o passivo
sempre aparece; o que muda é o carimbo e o motivo.** Omitir passivo é o inverso da
[[ADR-431]] — subdeclarar ativo deixa a prescrição mais cautelosa, subdeclarar
passivo a deixa mais agressiva.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

from pipeline.domain.services.money_parsing import valor_monetario_float

# Financiamento amortizante: o saldo do ano anterior é **teto** — amortização
# posterior não refletida erra para o lado conservador na prescrição. Fora desta
# lista (rotativo, cheque especial, `tipo` nulo) juros capitalizados podem ter
# **aumentado** o saldo, e o carimbo tem de dizer isso.
#
# Não bifurque a ROTA por `tipo`: ele é `null` por contrato quando a origem não
# classificou, e regra que depende dele falha aberta exatamente na linha mal
# classificada. O que bifurca é a direção declarada do erro.
_TIPOS_AMORTIZANTES: frozenset[str] = frozenset({"financiamento_veiculo", "consignado"})


class DirecaoDoErro(str, Enum):
    """Para que lado o saldo carimbado erra ([[ADR-431]] §Consequências)."""

    teto = "teto"
    indeterminado = "indeterminado"
    exato = "exato"


@dataclass(frozen=True)
class SaldoResolvido:
    """Saldo devedor de uma linha, com a proveniência temporal junto."""

    valor: Decimal
    ano: str | None
    carry_forward: bool = False
    quitada: bool = False
    direcao_do_erro: DirecaoDoErro = DirecaoDoErro.exato
    defasagem: int = 0
    """Anos entre o saldo publicado e o ano-base pedido; 0 quando casam."""
    apurado: bool = True
    """`False` quando a linha existe mas o saldo não é determinável em ano nenhum."""


def _dec(valor: Any) -> Decimal:
    """Dinheiro nunca é float em cálculo ([[ADR-090]])."""
    return Decimal(str(valor_monetario_float(valor)))


# `financiamento_imobiliario` fica no default porque o `indexador` que separa TR
# (amortizante) de IPCA+ (pode crescer) existe no baseline e **não é lido** pelo
# E5. Conservador na direção certa enquanto não for.
def _direcao(dv: Mapping[str, Any]) -> DirecaoDoErro:
    """Default é `indeterminado`: só sobe para `teto` com evidência do tipo."""
    tipo = dv.get("tipo")
    return DirecaoDoErro.teto if tipo in _TIPOS_AMORTIZANTES else DirecaoDoErro.indeterminado


# Discrimina *"a declaração daquele ano não cobriu dívidas"* (segue carry-forward)
# de *"cobriu e esta não está lá"* (é quitação). Sem ele, dívida efetivamente
# quitada seria ressuscitada para sempre.
def anos_declarados_por_membro(dividas: list[Mapping[str, Any]], pertence: Any) -> frozenset[str]:
    """Anos em que **este** membro declarou alguma dívida com saldo."""
    anos: set[str] = set()
    for dv in dividas:
        if not pertence(dv):
            continue
        saldo = dv.get("saldo_31_12")
        if isinstance(saldo, dict):
            anos |= {str(k) for k in saldo if str(k).isdigit()}
    return frozenset(anos)


# Ramos, na ordem: forma legada escalar (sem eixo de ano para divergir) · C1 o ano
# pedido existe · saldo sem nenhum ano legível · C3 a declaração do ano-base cobriu
# dívidas deste membro e esta não está lá, logo a ausência é evidência de QUITAÇÃO
# (zero DECLARADO, nunca mudo) · C2/C4 carry-forward.
#
# `anos_declarados` vazio preserva o comportamento histórico de `_resolve_saldo`
# (carry-forward puro): sem o discriminador, o fail-safe é **mostrar** o passivo.
def resolver_saldo(
    dv: Mapping[str, Any],
    ano_ref: str | None,
    *,
    anos_declarados: frozenset[str] = frozenset(),
) -> SaldoResolvido:
    """Saldo devedor no ano-base, ou o mais recente disponível — sempre declarado."""
    saldo = dv.get("saldo_31_12", 0)
    if not isinstance(saldo, dict):
        return SaldoResolvido(_dec(saldo), ano_ref)
    if ano_ref and ano_ref in saldo:
        return SaldoResolvido(_dec(saldo[ano_ref]), ano_ref)
    anos = sorted(k for k in saldo if str(k).isdigit())
    if not anos:
        return SaldoResolvido(Decimal(0), None, apurado=False)
    if ano_ref and ano_ref in anos_declarados:
        return SaldoResolvido(Decimal(0), ano_ref, quitada=True)
    return _carry_forward(dv, saldo, anos[-1], ano_ref)


def _carry_forward(
    dv: Mapping[str, Any], saldo: Mapping[str, Any], ano_saldo: str, ano_ref: str | None
) -> SaldoResolvido:
    """C2/C4 — publica o ano mais recente, com o carimbo e a direção do erro."""
    defasagem = 0
    if ano_ref and str(ano_ref).isdigit():
        defasagem = max(0, int(ano_ref) - int(ano_saldo))
    return SaldoResolvido(
        _dec(saldo[ano_saldo]),
        ano_saldo,
        carry_forward=True,
        direcao_do_erro=_direcao(dv),
        defasagem=defasagem,
    )


# Zero somado em silêncio é afirmação de que a família não deve aquilo ([[ADR-431]]).
# Quem consome o TOTAL precisa saber que ele está incompleto — sem isso o score
# credita nota máxima por um passivo que ninguém conseguiu ler.
def dividas_nao_apuradas(dividas: list[Mapping[str, Any]] | None) -> int:
    """Linhas de dívida cujo saldo não é determinável em ano nenhum."""
    return sum(1 for dv in (dividas or []) if not resolver_saldo(dv, None).apurado)
