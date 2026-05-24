"""Dedup canônico de TaskSuggestion — ADR-266.

Helper puro que normaliza (source, title, category) em chave determinística
sha256. Usado pelo dispatcher Celery (E5N) e pelo script de backfill em
`dev/backfill_task_suggestion_dedup.py`.

Decisões de normalização (ver ADR-266 §Decisão):
- inclui ``source`` no hash (evita colisão entre fontes futuras)
- normaliza ``title`` via lower + strip + colapsar whitespace
- normaliza ``category`` (mesmo padrão) — categoria é dimensão semântica
- NÃO inclui ``description`` (LLM varia rationale entre runs)
- NÃO inclui ``priority``/``deadline_*`` (cosmético; suscetível a flutuação)

Truncado para 64 chars — Postgres `VARCHAR(64)` + SQLite alinhado. 64
chars de sha256 ainda mantém >256 bits de entropia efetiva — colisão é
desprezível para inbox de proposta humana.
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

__all__ = ["compute_task_suggestion_dedup_key", "normalize_text"]


_WHITESPACE_RE: Final = re.compile(r"\s+")


def normalize_text(value: str | None) -> str:
    """Lower + strip + colapsar whitespace (estável entre runs)."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def compute_task_suggestion_dedup_key(source: str, title: str | None, category: str | None) -> str:
    """sha256(source:normalize(title):normalize(category))[:64] — ADR-266.

    `source` entra ``raw`` (já é enum curto e canônico em VALID_SUGGESTION_SOURCES).
    """
    payload = f"{source}:{normalize_text(title)}:{normalize_text(category)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:64]
