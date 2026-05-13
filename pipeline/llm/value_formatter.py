"""Value formatter compartilhado destilador ↔ tools (ADR-203 §D8, ADR-209)."""

from __future__ import annotations

from typing import Any, Literal

FormatHint = Literal["raw", "brl", "pct", "percent2", "int", "string", "iso_date"]

_VALID_FORMATS: frozenset[str] = frozenset(
    {"raw", "brl", "pct", "percent2", "int", "string", "iso_date"}
)


def format_value(value: Any, fmt: FormatHint = "raw") -> Any:
    """Aplica format hint a um valor (ADR-209: pct é valor absoluto)."""
    if fmt not in _VALID_FORMATS:
        raise ValueError(f"unknown format hint {fmt!r}; expected one of {sorted(_VALID_FORMATS)}")
    if fmt == "raw":
        return value
    if value is None:
        return "—"
    return _DISPATCH[fmt](value)


def _coerce_number(value: Any) -> float | None:
    """Converte int/float/str numérica para float. Retorna None se impossível."""
    if isinstance(value, bool):
        return None  # bool is int subclass — exclude
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", ".")
        if cleaned in ("", "N/D", "nan"):
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _format_brl(value: Any) -> str:
    n = _coerce_number(value)
    if n is None:
        return str(value)
    sign = "-" if n < 0 else ""
    n = abs(n)
    integer, frac = divmod(round(n * 100), 100)
    integer_str = f"{int(integer):,}".replace(",", ".")
    return f"{sign}R$ {integer_str},{int(frac):02d}"


def _format_pct(value: Any, *, decimals: int) -> str:
    n = _coerce_number(value)
    if n is None:
        return str(value)
    # ADR-209: valor já é absoluto; só formata casas decimais e troca ponto por vírgula.
    return f"{n:.{decimals}f}".replace(".", ",") + "%"


def _format_int(value: Any) -> str:
    n = _coerce_number(value)
    if n is None:
        return str(value)
    return str(int(round(n)))


_DISPATCH = {
    "brl": _format_brl,
    "pct": lambda v: _format_pct(v, decimals=1),
    "percent2": lambda v: _format_pct(v, decimals=2),
    "int": _format_int,
    "string": str,
    "iso_date": str,
}
