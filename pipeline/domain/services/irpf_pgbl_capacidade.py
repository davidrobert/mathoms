"""Regra dos 12% do PGBL — teto, aportado e restante como grandezas distintas.

Separada de ``irpf_analyzer`` (ADR-189/395): a regra é pura sobre uma lista de
declarações; o analyzer é o leitor que as monta. Módulo próprio também mantém o
analyzer abaixo do teto de 500 linhas.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

PGBL_TETO_PCT = Decimal("0.12")

_ZERO = Decimal("0")


class PgblStatus(str, Enum):
    """ADR-189: diagnóstico tipificado da capacidade PGBL (4 estados)."""

    capacidade_disponivel = "capacidade_disponivel"
    modelo_simplificado = "modelo_simplificado"
    no_teto = "no_teto"
    sem_renda_tributavel = "sem_renda_tributavel"


@dataclass(frozen=True)
class PgblResumo:
    """ADR-189 §D2: aporte e teto dedutível no ano."""

    aportado_brl: Decimal
    teto_brl: Decimal


@dataclass(frozen=True)
class DeclaracaoPgbl:
    """O que a regra dos 12% precisa saber de cada CPF, e nada mais."""

    simplificada: bool
    renda_tributavel: Decimal
    pgbl_aportado: Decimal

    @property
    def teto(self) -> Decimal:
        """Zero na simplificada: o desconto padrão substitui as deduções legais."""
        return _ZERO if self.simplificada else self.renda_tributavel * PGBL_TETO_PCT


# O escalar que este VO substitui (ADR-402) fazia o mesmo `0` significar três
# fatos: modelo simplificado (não há teto), teto consumido (restante zerado) e
# aporte ACIMA do teto — este último apagado pelo `max(0, ...)` e o mais
# acionável dos três. `teto is None` ⇔ não há base dedutível de 12% no ano.
@dataclass(frozen=True)
class CapacidadePgbl:
    """Capacidade PGBL do ano: teto, aportado e restante em campos próprios."""

    teto: Decimal | None
    aportado: Decimal
    restante: Decimal | None
    status: PgblStatus
    excedente_nao_dedutivel: Decimal


def resumo_pgbl(decls: list[DeclaracaoPgbl]) -> PgblResumo:
    return PgblResumo(
        aportado_brl=sum((d.pgbl_aportado for d in decls), _ZERO),
        teto_brl=sum((d.teto for d in decls), _ZERO),
    )


# Clamp e teto são POR DECLARAÇÃO porque o limite de 12% é por CPF: somar antes
# de clampar deixaria o excesso de um titular consumir o espaço do outro.
def capacidade_pgbl(decls: list[DeclaracaoPgbl], renda_tributavel_total: Decimal) -> CapacidadePgbl:
    """Teto, aportado e restante do ano — VO, não escalar (ADR-402)."""
    teto = sum((d.teto for d in decls), _ZERO)
    restante = sum((max(d.teto - d.pgbl_aportado, _ZERO) for d in decls), _ZERO)
    tem_teto = teto > _ZERO
    return CapacidadePgbl(
        teto=teto if tem_teto else None,
        aportado=sum((d.pgbl_aportado for d in decls), _ZERO),
        restante=restante if tem_teto else None,
        status=_status(decls, renda_tributavel_total, restante if tem_teto else None),
        excedente_nao_dedutivel=sum((max(d.pgbl_aportado - d.teto, _ZERO) for d in decls), _ZERO),
    )


def _status(
    decls: list[DeclaracaoPgbl], renda_tributavel_total: Decimal, restante: Decimal | None
) -> PgblStatus:
    if decls and all(d.simplificada for d in decls):
        return PgblStatus.modelo_simplificado
    if renda_tributavel_total == _ZERO:
        return PgblStatus.sem_renda_tributavel
    if restante is not None and restante > _ZERO:
        return PgblStatus.capacidade_disponivel
    return PgblStatus.no_teto
