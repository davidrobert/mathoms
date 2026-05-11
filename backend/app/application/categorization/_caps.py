"""Caps + constantes compartilhadas (ADR-188 §D6 · A12 P3 PR2)."""

from __future__ import annotations

from pipeline.domain.services.categorization_service import (
    RULE_HARD_CAP,
    RULE_SOFT_CAP,
)

# Threshold para warning ``keyword_too_short`` (ADR-188 §D5 — UX).
# UI usa para alertar; não bloqueia criação.
KEYWORD_TOO_SHORT_THRESHOLD: int = 4

# Threshold acima do qual apply síncrono é proibido (PR3 troca por Celery async).
# Conservador: 500 overrides * ~5ms cada = 2.5s na pior hipótese. Excede SLA.
SYNC_APPLY_THRESHOLD: int = 500

__all__ = [
    "KEYWORD_TOO_SHORT_THRESHOLD",
    "RULE_HARD_CAP",
    "RULE_SOFT_CAP",
    "SYNC_APPLY_THRESHOLD",
]
