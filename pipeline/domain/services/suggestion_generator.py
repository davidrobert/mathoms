"""SuggestionGenerator — dispatcher determinístico das regras canônicas.

Função pura: snapshot E5 (dict) → list[SuggestionDraft] ranqueada
(severidade desc → valor desc) e truncada em :data:`SUGGESTION_CAP`.

Sem I/O. Persistência (FK report, dedup, transação) é responsabilidade
de :func:`backend.app.application.suggestions.regenerate_for_report`.

Boundary do pipeline (ADR-101 / `dev/check_pipeline_boundaries.py`):
não importa ``backend.*``. Ver :mod:`pipeline.domain.services.suggestion_rules`
para a tabela de regras (5 v1 ADR-153 com rationale enriquecido por
Onda 10 #5 + 6 v2 ADR-161 Cerbasi/AUVP/Perini completos).
"""

from __future__ import annotations

from typing import Any

from pipeline.domain.services.suggestion_config import SuggestionGeneratorConfig
from pipeline.domain.services.suggestion_rules import ALL_RULES
from pipeline.domain.types.suggestion import SuggestionDraft

SUGGESTION_CAP: int = 8
"""Cap por re-geração — ADR-161 sobe de 6 → 8 (11 regras candidatas)."""

DISMISS_RESPECT_WINDOW_DAYS: int = 90
"""Janela de respeito a Descartadas — re-aparecem após este prazo."""


_SEVERITY_RANK = {"danger": 3, "warning": 2, "info": 1}


def _rank_key(draft: SuggestionDraft) -> tuple[int, int]:
    sev = _SEVERITY_RANK.get(draft.severity, 0)
    amount = int(draft.amount_brl * 100) if draft.amount_brl is not None else 0
    return (sev, amount)


class SuggestionGenerator:
    """Aplica regras canônicas v1+v2 sobre o snapshot E5."""

    def __init__(self, config: SuggestionGeneratorConfig | None = None) -> None:
        self._config = config or SuggestionGeneratorConfig()

    def generate(self, snapshot: dict[str, Any]) -> list[SuggestionDraft]:
        drafts = [
            d
            for d in (_safe_apply(rule, snapshot, self._config) for rule in ALL_RULES)
            if d is not None
        ]
        drafts.sort(key=_rank_key, reverse=True)
        return drafts[:SUGGESTION_CAP]


def _safe_apply(
    rule, snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    try:
        return rule(snapshot, cfg)
    except (KeyError, TypeError, ValueError):
        return None


__all__ = [
    "DISMISS_RESPECT_WINDOW_DAYS",
    "SUGGESTION_CAP",
    "SuggestionGenerator",
    "SuggestionGeneratorConfig",
]
