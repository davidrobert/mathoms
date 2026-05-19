"""Normaliza account_number heterogêneo entre parsers E2 (ADR-226 §1)."""

from __future__ import annotations

import re

_NON_DIGITS = re.compile(r"\D")


def normalize_account_number(raw: str | None) -> str | None:
    """Retorna apenas dígitos, ou None se vazio (`'12.345-6'` → `'123456'`)."""
    if not raw:
        return None
    digits = _NON_DIGITS.sub("", raw)
    return digits or None
