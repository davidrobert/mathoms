"""BRL em prosa pt-BR (A40.l51 C2/C3). Sem compactação k/M — isso é I2."""

from __future__ import annotations

from decimal import Decimal


def fmt_brl_prosa(value: object, *, decimals: int = 0) -> str:
    """``R$ 2.000`` ou ``R$ 2.000,50``. Nunca ``R$ 2,000``."""
    quantum = Decimal("0.01") if decimals else Decimal("1")
    quantized = Decimal(str(value)).quantize(quantum)
    if decimals == 0:
        return f"R$ {int(quantized):,}".replace(",", ".")
    swapped = f"{quantized:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {swapped}"
