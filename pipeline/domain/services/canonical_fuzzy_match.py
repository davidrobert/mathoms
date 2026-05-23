"""Fuzzy match de canonicals de PropertyIdentity por proximidade numérica (ADR-265)."""

from __future__ import annotations

import re

# Identificadores estáveis (mat:/qa:/iptu:) só casam string-equal. Fuzzy
# não se aplica porque a evidência é mais forte que via+numero.
_STRONG_PREFIXES: tuple[str, ...] = ("mat:", "qa:", "iptu:")

_VIA_NUMBER_PATTERN = re.compile(r"^(.+?)\s+(\d+)$")

# Complemento (apto/bloco/torre/unidade) disambigua quando via+numero são
# próximos. Ordem importa: padrões específicos primeiro.
_COMPLEMENTO_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bapto?\.?\s*(\d{1,5})\b", re.IGNORECASE),
    re.compile(r"\bap\.?\s*(\d{1,5})\b", re.IGNORECASE),
    re.compile(r"\bunidade\s*(\d{1,5})\b", re.IGNORECASE),
    re.compile(r"\bbloco\s*([\w-]{1,5})\b", re.IGNORECASE),
    re.compile(r"\btorre\s*([\w-]{1,5})\b", re.IGNORECASE),
)


def _has_strong_prefix(canonical: str) -> bool:
    return any(canonical.startswith(p) for p in _STRONG_PREFIXES)


def _parse_via_numero(canonical: str) -> tuple[str, int] | None:
    """Extrai (via, numero) do canonical `<via> <numero>` — None se malformado."""
    match = _VIA_NUMBER_PATTERN.match(canonical)
    if match is None:
        return None
    via, numero = match.group(1).strip(), match.group(2)
    if not via or not numero:
        return None
    return via, int(numero)


def extract_complemento(descricao: str | None) -> str | None:
    """Extrai complemento canônico (apto/bloco/torre) — None se ausente."""
    if not descricao:
        return None
    for pattern in _COMPLEMENTO_PATTERNS:
        match = pattern.search(descricao)
        if match is not None:
            return match.group(1).lower().strip()
    return None


def _complementos_divergem(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() != b.strip().lower()


def _complementos_iguais(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


def _eligible_for_fuzzy(canonical_a: str, canonical_b: str) -> bool:
    if not canonical_a or not canonical_b:
        return False
    return not (_has_strong_prefix(canonical_a) or _has_strong_prefix(canonical_b))


def matches_fuzzy(
    canonical_a: str | None,
    canonical_b: str | None,
    *,
    max_number_diff: int = 4,
    max_with_complemento_match: int = 8,
    complemento_a: str | None = None,
    complemento_b: str | None = None,
) -> bool:
    """True se mesmo imóvel via proximidade numérica (ADR-265)."""
    pair = _parsed_pair(canonical_a, canonical_b)
    if pair is None or _complementos_divergem(complemento_a, complemento_b):
        return False
    diff = abs(pair[0][1] - pair[1][1])
    if diff <= max_number_diff:
        return True
    return _complementos_iguais(complemento_a, complemento_b) and diff <= max_with_complemento_match


def _parsed_pair(a: str | None, b: str | None) -> tuple[tuple[str, int], tuple[str, int]] | None:
    if not a or not b or not _eligible_for_fuzzy(a, b):
        return None
    parsed_a = _parse_via_numero(a)
    parsed_b = _parse_via_numero(b)
    if parsed_a is None or parsed_b is None or parsed_a[0] != parsed_b[0]:
        return None
    return parsed_a, parsed_b


__all__ = [
    "extract_complemento",
    "matches_fuzzy",
]
