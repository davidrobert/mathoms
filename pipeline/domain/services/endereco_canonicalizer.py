"""Normalização de endereço para matching de imóveis cross-IRPFs (ADR-215, ADR-225)."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

_logger = logging.getLogger("mathoms.property_identity")

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


# ADR-225 §1 — cascade signal patterns (fallback quando via+numero falha).
# Order matters em canonicalize(): via+numero primeiro (backward-compat),
# então matrícula > QA > IPTU (estabilidade cross-fonte decrescente).

# Matrícula: regex inicial aceita ≥4 caracteres (com pontos); normalização
# pós-match exige ≥4 dígitos puros (anti-OCR ruim como "matrícula 12").
_MATRICULA_PATTERN = re.compile(
    r"matr[íi]cula[\s.:#nº°]*([\d.]{4,})",
    flags=re.IGNORECASE,
)

# Código QuintoAndar: "Cód. Imóvel QuintoAndar: 894064293" etc.
_QUINTOANDAR_PATTERN = re.compile(
    r"quintoandar[\s:]*(\d+)",
    flags=re.IGNORECASE,
)

# IPTU / Inscrição Municipal: aceita formatos diversos
# ("087.006.0478-1", "30105434946", "087.006.0478/1"). Permite até 30 chars não-dígitos
# entre o rótulo e o número (cobre "Inscrição Municipal (IPTU): NNN").
# Mín. 6 dígitos pós-normalização.
_IPTU_PATTERN = re.compile(
    r"(?:iptu|inscri[cç][aã]o\s*municipal)[^\d\n]{0,30}([\d./\-]{6,})",
    flags=re.IGNORECASE,
)

# Cidade/UF para namespace de matrícula: detecção robusta entre formatos
# variados ("SAO PAULO/SP", "São Paulo - SP", "Cyrela Campinas - SP") é
# complexa o suficiente pra valer ADR/PR próprio. Por ora, namespace é
# apenas `mat:NNN`. Cross-cartório collision (matrícula coincidente entre
# CRIs em cidades distintas) fica como follow-up — risco baixo para
# workspaces atuais. Ver ADR-225 §Follow-ups.


def _extract_matricula(descricao: str) -> Optional[str]:
    """Matrícula RFB sem pontos (≥4 dígitos)."""
    match = _MATRICULA_PATTERN.search(descricao)
    if match is None:
        return None
    digits = re.sub(r"[^\d]", "", match.group(1))
    if len(digits) < 4:
        return None
    return digits


def _extract_quintoandar(descricao: str) -> Optional[str]:
    """Código QuintoAndar (apenas dígitos)."""
    match = _QUINTOANDAR_PATTERN.search(descricao)
    return match.group(1) if match else None


def _extract_iptu(descricao: str) -> Optional[str]:
    """IPTU/Inscrição municipal sem pontuação (≥6 dígitos)."""
    match = _IPTU_PATTERN.search(descricao)
    if match is None:
        return None
    digits = re.sub(r"[^\d]", "", match.group(1))
    if len(digits) < 6:
        return None
    return digits


def _format_via_numero(extracted: tuple[str, str]) -> str:
    """`<via> <numero>` — formato legado backward-compat."""
    return f"{extracted[0]} {extracted[1]}"


# Cascade tabela (ADR-225 §1): (extractor, cascade_level, formatter).
# Order matters — via+numero primeiro preserva canonical de rows existentes.
_CASCADE: tuple[tuple, ...] = (
    (extract_via_numero, "via_numero", _format_via_numero),
    (_extract_matricula, "mat", lambda v: f"mat:{v}"),
    (_extract_quintoandar, "qa", lambda v: f"qa:{v}"),
    (_extract_iptu, "iptu", lambda v: f"iptu:{v}"),
)


def canonicalize(descricao: str) -> Optional[str]:
    """Canonical key via cascata via+numero > matrícula > QA > IPTU (ADR-225 §1).

    Emite log `mathoms.property_identity.cascade_hit{level=…}` para
    observabilidade da qualidade do canonicalizer.
    """
    if not descricao:
        return None
    for extractor, level, fmt in _CASCADE:
        result = extractor(descricao)
        if result is not None:
            _logger.info("canonicalizer.cascade_hit", extra={"cascade_level": level})
            return fmt(result)
    _logger.info("canonicalizer.cascade_hit", extra={"cascade_level": "none"})
    return None


__all__ = [
    "normalize",
    "extract_via_numero",
    "canonicalize",
]
