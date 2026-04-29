"""Use case: lista Suggestions do workspace (filtra opcionalmente por status)."""

from __future__ import annotations

from typing import Optional

from backend.app.application.base.errors import ValidationError
from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.models.suggestion import VALID_SUGGESTION_AGGREGATE_STATUSES
from backend.app.schemas.dto.suggestion import (
    SuggestionListResponse,
    suggestion_to_response,
)


async def list_suggestions(
    workspace_id: str,
    *,
    status: Optional[str] = None,
    repo: SuggestionRepositoryProtocol,
) -> SuggestionListResponse:
    if status is not None and status not in VALID_SUGGESTION_AGGREGATE_STATUSES:
        raise ValidationError(
            f"status inválido: {status!r}; aceitos: {sorted(VALID_SUGGESTION_AGGREGATE_STATUSES)}",
            code="invalid_status_filter",
        )
    rows = await repo.list_by_workspace(workspace_id, status=status)
    items = [suggestion_to_response(s) for s in rows]
    return SuggestionListResponse(suggestions=items, total=len(items))
