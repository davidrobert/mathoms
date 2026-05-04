"""Use case: sumário de Suggestions pendentes (ADR-161 · Onda 8 #5).

Substitui o ``count_suggestions`` em call-sites que precisam refletir
severidade (banner em /plano). Retorna count + max_severity + by_category
para a UI:
- ``count``: total pendente.
- ``max_severity``: severidade dominante (`danger` > `warning` > `info`)
  determina tom do banner (vermelho/amarelo/azul).
- ``by_category``: contagem agrupada (ADR-161) para tooltip/filtro.
"""

from __future__ import annotations

from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.schemas.dto.suggestion import SuggestionsSummaryResponse

_SEVERITY_RANK = {"danger": 3, "warning": 2, "info": 1}


async def get_pending_summary(
    workspace_id: str,
    *,
    repo: SuggestionRepositoryProtocol,
) -> SuggestionsSummaryResponse:
    pending = await repo.list_by_workspace(workspace_id, status="Pendente")
    if not pending:
        return SuggestionsSummaryResponse(count=0, max_severity=None, by_category={})
    max_severity = _max_severity(pending)
    by_category = _group_by_category(pending)
    return SuggestionsSummaryResponse(
        count=len(pending),
        max_severity=max_severity,
        by_category=by_category,
    )


def _max_severity(suggestions) -> str:
    """Retorna severidade dominante (max via _SEVERITY_RANK)."""
    return max(suggestions, key=lambda s: _SEVERITY_RANK.get(s.severity, 0)).severity


def _group_by_category(suggestions) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in suggestions:
        key = s.category or "uncategorized"
        counts[key] = counts.get(key, 0) + 1
    return counts
