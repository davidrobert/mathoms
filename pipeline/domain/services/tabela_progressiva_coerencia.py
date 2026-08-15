"""Invariantes de coerência da tabela progressiva do IRPF ([[ADR-389]] D3 · A40.l56)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from pipeline.domain.types.config import IRPFBracket

# Resíduo máximo tolerado na continuidade entre faixas. Medido nas 12 fronteiras
# de 2024-2026 (as duas tabelas): o pior desvio real é R$ 0,005, puro
# arredondamento da parcela publicada ao centavo. R$ 0,05 — a tolerância que a
# A40.l56 propunha antes da medição — é 10× o ruído e deixaria passar erro
# genuíno de um centavo em parcela.
TOLERANCIA_CONTINUIDADE_CENTS = Decimal("1")

# Acima disto, a divergência anual vs 12× mensal deixa de ser arredondamento e
# exige `motivo` declarado na row. Calibrado: em ano de transição a divergência
# é de R$ 147,20 (2024) a R$ 678,40 (2025); em ano limpo, R$ 0,10.
LIMIAR_DIVERGENCIA_X12_CENTS = Decimal("100")


@dataclass(frozen=True)
class Violacao:
    """Onde a tabela quebrou — carrega a fronteira, não um booleano."""

    invariante: str
    indice_faixa: int
    detalhe: str

    def format(self) -> str:
        return f"[{self.invariante}] faixa {self.indice_faixa}: {self.detalhe}"


def _imposto(base_cents: int, faixa: IRPFBracket) -> Decimal:
    return Decimal(base_cents) * faixa.aliquota_pct / Decimal(100) - Decimal(
        faixa.deducao_brl_cents
    )


def verificar_continuidade(faixas: Sequence[IRPFBracket]) -> tuple[Violacao, ...]:
    """No teto de cada faixa, o imposto pelas duas faixas adjacentes coincide."""
    violacoes = []
    for i in range(len(faixas) - 1):
        teto = faixas[i].upper_brl_cents
        if teto is None:
            violacoes.append(Violacao("continuidade", i, "faixa terminal antes do fim da tabela"))
            continue
        residuo = _imposto(teto, faixas[i + 1]) - _imposto(teto, faixas[i])
        if abs(residuo) > TOLERANCIA_CONTINUIDADE_CENTS:
            violacoes.append(
                Violacao(
                    "continuidade",
                    i,
                    f"resíduo de {residuo} cents no teto {teto} "
                    f"(tolerância {TOLERANCIA_CONTINUIDADE_CENTS})",
                )
            )
    return tuple(violacoes)


def verificar_primeira_fronteira(faixas: Sequence[IRPFBracket]) -> tuple[Violacao, ...]:
    """``upper[0] × aliquota[1] == deducao[1]``, EXATO — é aqui que vintage misturado aparece."""
    if len(faixas) < 2 or faixas[0].upper_brl_cents is None:
        return (Violacao("primeira_fronteira", 0, "tabela sem faixa isenta com teto"),)
    esperado = Decimal(faixas[0].upper_brl_cents) * faixas[1].aliquota_pct / Decimal(100)
    observado = Decimal(faixas[1].deducao_brl_cents)
    if esperado != observado:
        return (
            Violacao(
                "primeira_fronteira",
                1,
                f"deducao {observado} != {esperado} = teto isento "
                f"{faixas[0].upper_brl_cents} × {faixas[1].aliquota_pct}%; "
                f"desvio de {observado - esperado} cents indica vintages misturados",
            ),
        )
    return ()


def verificar_congruencia(
    mensal: Sequence[IRPFBracket], anual: Sequence[IRPFBracket]
) -> tuple[Violacao, ...]:
    """As duas tabelas são a mesma estrutura de faixas em periodicidades distintas."""
    if len(mensal) != len(anual):
        return (
            Violacao(
                "congruencia",
                0,
                f"cardinalidade difere: mensal={len(mensal)} anual={len(anual)}",
            ),
        )
    violacoes = []
    for i, (m, a) in enumerate(zip(mensal, anual)):
        if m.aliquota_pct != a.aliquota_pct:
            violacoes.append(
                Violacao("congruencia", i, f"alíquota {m.aliquota_pct} vs {a.aliquota_pct}")
            )
        if (m.upper_brl_cents is None) != (a.upper_brl_cents is None):
            violacoes.append(Violacao("congruencia", i, "terminal em posições diferentes"))
    return tuple(violacoes)


def _teto_regride(atual: IRPFBracket, seguinte: IRPFBracket) -> bool:
    if atual.upper_brl_cents is None or seguinte.upper_brl_cents is None:
        return False
    return seguinte.upper_brl_cents <= atual.upper_brl_cents


def _violacao_do_par(i: int, atual: IRPFBracket, seguinte: IRPFBracket) -> Violacao | None:
    if _teto_regride(atual, seguinte):
        return Violacao(
            "monotonicidade",
            i,
            f"teto não cresce: {atual.upper_brl_cents} → {seguinte.upper_brl_cents}",
        )
    if seguinte.deducao_brl_cents < atual.deducao_brl_cents:
        return Violacao(
            "monotonicidade",
            i,
            f"dedução decresce: {atual.deducao_brl_cents} → {seguinte.deducao_brl_cents}",
        )
    return None


def verificar_monotonicidade(faixas: Sequence[IRPFBracket]) -> tuple[Violacao, ...]:
    """Teto estritamente crescente; dedução não-decrescente."""
    pares = zip(faixas, faixas[1:])
    achados = (_violacao_do_par(i, a, b) for i, (a, b) in enumerate(pares))
    return tuple(v for v in achados if v is not None)


def divergencia_x12(mensal: Sequence[IRPFBracket], anual: Sequence[IRPFBracket]) -> tuple[int, ...]:
    """Índices onde |anual − 12×mensal| excede o limiar e exige ``motivo`` na row."""
    indices = []
    for i, (m, a) in enumerate(zip(mensal, anual)):
        delta = abs(Decimal(a.deducao_brl_cents) - Decimal(m.deducao_brl_cents) * 12)
        if delta > LIMIAR_DIVERGENCIA_X12_CENTS:
            indices.append(i)
            continue
        if m.upper_brl_cents is None or a.upper_brl_cents is None:
            continue
        delta_teto = abs(Decimal(a.upper_brl_cents) - Decimal(m.upper_brl_cents) * 12)
        if delta_teto > LIMIAR_DIVERGENCIA_X12_CENTS:
            indices.append(i)
    return tuple(indices)


__all__ = [
    "LIMIAR_DIVERGENCIA_X12_CENTS",
    "TOLERANCIA_CONTINUIDADE_CENTS",
    "Violacao",
    "divergencia_x12",
    "verificar_congruencia",
    "verificar_continuidade",
    "verificar_monotonicidade",
    "verificar_primeira_fronteira",
]
