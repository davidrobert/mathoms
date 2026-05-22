"""Identidade determinística de transações para dedup cross-document (ADR-248)."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )


def normalize_banco(value: str | None) -> str:
    """Robust contra drift de casing/espacing (`"C6Bank"` vs `"C6 Bank"`)."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_titular(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_tipo_conta(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_descricao(value: str | None) -> str:
    """Lowercase + strip + colapsa whitespace — preserva acento + tokens N/M."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def cents_int(valor: float | int) -> int:
    """Converte ``valor`` para int em centavos (evita float drift, ADR-090 §wire)."""
    return int(round(float(valor) * 100))


def compute_transaction_hash(
    *,
    data: str | None,
    banco: str | None,
    titular: str | None,
    tipo_conta: str | None,
    valor: float | int,
    descricao: str | None,
) -> str:
    """sha256[:16] determinístico — chave K4 da ADR-248 (sinal em ``kind``)."""
    parts = (
        data or "",
        normalize_banco(banco),
        normalize_titular(titular),
        normalize_tipo_conta(tipo_conta),
        str(cents_int(abs(valor))),
        normalize_descricao(descricao),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
