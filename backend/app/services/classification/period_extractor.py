"""Period extraction from financial document text (YYYYMM and date ranges)."""

from __future__ import annotations

import re

_PERIOD_RANGE_RE = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4}).{0,20}?(?:a|at[eé]|to|-)\s*(\d{1,2})/(\d{1,2})/(\d{4})",
    re.I | re.DOTALL,
)
_YYYYMM_RE = re.compile(r"\b(20\d{2})[-/](0?[1-9]|1[012])\b")
_MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_MONTH_YEAR_BR_RE = re.compile(
    r"\b(jan(?:eiro)?|fev(?:ereiro)?|mar(?:[çc]o)?|abr(?:il)?|mai(?:o)?|jun(?:ho)?|"
    r"jul(?:ho)?|ago(?:sto)?|set(?:embro)?|out(?:ubro)?|nov(?:embro)?|dez(?:embro)?)"
    r"[\s/\-]+(20\d{2})",
    re.I,
)


def _mm(month_name: str) -> int:
    key = month_name.lower()[:3]
    for full, n in _MESES.items():
        if full.startswith(key):
            return n
    return 0


def extract_period_from_content(text: str) -> str | None:
    """Try to extract a YYYYMM or YYYYMM_YYYYMM period from document text."""
    m = _PERIOD_RANGE_RE.search(text)
    if m:
        _, m1, y1, _, m2, y2 = m.groups()
        return f"{int(y1):04d}{int(m1):02d}_{int(y2):04d}{int(m2):02d}"
    m = _YYYYMM_RE.search(text)
    if m:
        y, mn = m.groups()
        return f"{int(y):04d}{int(mn):02d}"
    m = _MONTH_YEAR_BR_RE.search(text)
    if m:
        name, year = m.groups()
        mn = _mm(name)
        if mn:
            return f"{int(year):04d}{mn:02d}"
    # Year-only fallback
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return m.group(1)
    return None
