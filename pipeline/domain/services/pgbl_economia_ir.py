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
from pipeline.domain.types.config import IRPFBracket


def _cents(valor: Decimal) -> int:
    return int(valor * 100)


def economia_diferencial(
    base_tributavel_anual: Decimal,
    aporte_dedutivel_anual: Decimal,
    faixas: tuple[IRPFBracket, ...],
) -> Decimal:
    """``IR(base) − IR(base − aporte)`` em reais; zero quando não há imposto a reduzir."""
    base_cents = _cents(base_tributavel_anual)
    com_aporte = max(0, base_cents - _cents(aporte_dedutivel_anual))
    delta = ir_devido_anual(base_cents, faixas) - ir_devido_anual(com_aporte, faixas)
    return Decimal(delta) / Decimal("100")
