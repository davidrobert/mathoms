"""Helper de custo essencial mensal (Track T06 · [[ADR-191]] §D4)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal

_ZERO = Decimal("0")


def compute_custo_essencial_mensal(
    despesas_mensais_por_categoria: Mapping[str, Decimal],
    categorias_in: Iterable[str],
) -> Decimal:
    """Soma despesa mensal média das ``categorias_in``; categorias fora da lista são ignoradas."""
    canonical = frozenset(str(c) for c in categorias_in)
    total = _ZERO
    for categoria, valor in despesas_mensais_por_categoria.items():
        if str(categoria) in canonical:
            total += _coerce_decimal(valor)
    return total


def _coerce_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool) or value is None:
        return _ZERO
    if isinstance(value, (int, str)):
        try:
            return Decimal(value)
        except Exception:
            return _ZERO
    if isinstance(value, float):
        return Decimal(str(value))
    return _ZERO


__all__ = ["compute_custo_essencial_mensal"]
