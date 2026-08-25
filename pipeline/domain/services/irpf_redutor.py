"""Redutor do imposto apurado — Lei 15.270/2025 ([[ADR-414]] D3).

Indexado no rendimento **bruto**, não na base de cálculo: é o que torna as duas
variáveis irredutíveis uma à outra (D1). O art. 11-A da Lei 9.250/1995 limita a
redução ao imposto apurado — não gera crédito —, e é esse clamp **por lado** que
produz toda a não-linearidade da economia de PGBL.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pipeline.domain.types.config import RedutorIRPF


def redutor_devido(
    bruto_anual_brl_cents: int, ir_apurado_brl_cents: int, redutor: RedutorIRPF
) -> int:
    """Redução efetiva em cents: bandas da norma, clampada ao imposto apurado."""
    if ir_apurado_brl_cents <= 0 or not redutor.vigente:
        return 0
    return min(_bruto_da_banda(bruto_anual_brl_cents, redutor), ir_apurado_brl_cents)


def _bruto_da_banda(bruto_cents: int, r: RedutorIRPF) -> int:
    if bruto_cents <= r.piso_bruto_brl_cents:
        # Banda 1: a norma zera o imposto. O teto declarado (R$ 2.694,15 no anual)
        # é o imposto no piso da banda — propriedade DERIVADA, nunca armazenada:
        # guardá-la deixaria a row capaz de discordar de si mesma.
        return r.intercepto_brl_cents
    if bruto_cents > r.teto_bruto_brl_cents:
        return 0
    bruta = Decimal(r.intercepto_brl_cents) - r.coeficiente * Decimal(bruto_cents)
    return max(0, int(bruta.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
