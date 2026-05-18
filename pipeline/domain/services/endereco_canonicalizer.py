"""Normalização de endereço para matching de imóveis cross-IRPFs (ADR-215)."""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

# Pares de abreviação → forma plena. Order matters: padrões mais longos primeiro.
_ABBREVIATION_MAP: tuple[tuple[str, str], ...] = (
    (r"\bav\.?\b", "avenida"),
    (r"\br\.?\b", "rua"),
    (r"\brod\.?\b", "rodovia"),
    (r"\best\.?\b", "estrada"),
    (r"\btv\.?\b", "travessa"),
    (r"\bal\.?\b", "alameda"),
    (r"\bpc\.?\b", "praca"),
    (r"\bapto?\.?\b", ""),
    (r"\bap\.?\b", ""),
    (r"\bbl\.?\b", ""),
    (r"\bn[º°]\b", ""),
    (r"\bno\b", ""),
)

# Tokens irrelevantes (palavras-cola) — removidos antes do compare.
_STOPWORDS = frozenset(
    {
        "rua",
        "avenida",
        "rodovia",
        "estrada",
        "travessa",
        "alameda",
        "praca",
        "de",
        "da",
        "do",
        "das",
        "dos",
        "e",
    }
)

# Pattern para extrair (logradouro, número). Aceita endereços em formato livre
# como "Rua Tasso da Silveira, 61", "AV ALBERTO AUGUSTO ALVES 320", "Av Paulista 1500 apt 42".
_VIA_NUMBER_PATTERN = re.compile(
    r"(?:rua|avenida|rodovia|estrada|travessa|alameda|praca)\s+"
    r"([\w\s]+?)\s*,?\s*"
    r"(\d{1,6})"
    r"(?!\d)",
    flags=re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


# Pré-limpeza removida antes da expansão de abreviações. Sem isso, "R$"
# vira "r$" → `\br\.?\b` matcha o "r" e produz "rua $ 80.000" → o regex
# de extração captura `(via="8", numero="0")` em descrições com preço.
_PRE_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    # Currency markers
    (r"r\$", " "),
    (r"u\$\s*\$?", " "),  # "U$$" ou "U$" (dólar comum em IRPF)
)


def normalize(text: str) -> str:
    """Lowercase, sem acento, com abreviações expandidas e espaços colapsados."""
    if not text:
        return ""
    out = _strip_accents(text).lower()
    # Strip currency markers ANTES da expansão de abreviações (B1 fix).
    for pattern, replacement in _PRE_SUBSTITUTIONS:
        out = re.sub(pattern, replacement, out)
    for pattern, replacement in _ABBREVIATION_MAP:
        out = re.sub(pattern, replacement, out)
    out = re.sub(r"[^\w\s]", " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _is_plausible_logradouro(tokens: list[str]) -> bool:
    """Logradouro real tem pelo menos 1 token alfabético de >=3 chars."""
    return any(t.isalpha() and len(t) >= 3 for t in tokens)


def extract_via_numero(descricao: str) -> Optional[tuple[str, str]]:
    """Extrai `(via, numero)` da descrição livre — None se não casa."""
    normalized = normalize(descricao)
    match = _VIA_NUMBER_PATTERN.search(normalized)
    if match is None:
        return None
    via_raw, numero = match.group(1), match.group(2)
    via_tokens = [t for t in via_raw.split() if t and t not in _STOPWORDS]
    if not via_tokens or not _is_plausible_logradouro(via_tokens):
        return None
    return (" ".join(via_tokens), numero)


def canonicalize(descricao: str) -> Optional[str]:
    """Canonical key `"<via_tokens> <numero>"` para `endereco_canonical` (ADR-215)."""
    extracted = extract_via_numero(descricao)
    if extracted is None:
        return None
    via, numero = extracted
    return f"{via} {numero}"


__all__ = ["normalize", "extract_via_numero", "canonicalize"]
