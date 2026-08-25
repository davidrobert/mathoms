"""Economia de IR de um aporte PGBL — o diferencial da [[ADR-375]] D5.

O `limite × alíquota_marginal` que este módulo encerra só acerta quando o aporte
não atravessa degrau da tabela; atravessar é o caso comum, porque o aporte
dedutível é 12% da própria base. Quando o redutor da Lei 15.270/2025 for
modelado ([[A40.l64]] PR3), ele compõe AQUI — é função do rendimento bruto e não
se move com o aporte, então entra dos dois lados da diferença.
"""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.irpf_faixa_marginal import ir_devido_anual
from pipeline.domain.services.irpf_redutor import redutor_devido
from pipeline.domain.types.config import IRPFBracket, RedutorIRPF


def _cents(valor: Decimal) -> int:
    return int(valor * 100)


# O redutor não se move com o aporte (indexa o BRUTO), então entra dos dois lados
# — mas o clamp ao imposto apurado é POR LADO, e é ele que torna a economia
# não-linear: o lado com aporte pode clipar enquanto o outro não ([[ADR-414]] D4).
def economia_diferencial(
    base_tributavel_anual: Decimal,
    aporte_dedutivel_anual: Decimal,
    faixas: tuple[IRPFBracket, ...],
    bruto_anual: Decimal | None = None,
    redutor: RedutorIRPF | None = None,
) -> Decimal:
    """``IR_pós(base) − IR_pós(base − aporte)`` em reais, já líquido do redutor."""
    base_cents = _cents(base_tributavel_anual)
    com_aporte = max(0, base_cents - _cents(aporte_dedutivel_anual))
    bruto_cents = _cents(bruto_anual) if bruto_anual is not None else 0
    delta = _ir_pos_redutor(base_cents, bruto_cents, faixas, redutor) - _ir_pos_redutor(
        com_aporte, bruto_cents, faixas, redutor
    )
    return Decimal(delta) / Decimal("100")


def _ir_pos_redutor(
    base_cents: int,
    bruto_cents: int,
    faixas: tuple[IRPFBracket, ...],
    redutor: RedutorIRPF | None,
) -> int:
    ir = ir_devido_anual(base_cents, faixas)
    if redutor is None:
        return ir
    return ir - redutor_devido(bruto_cents, ir, redutor)
