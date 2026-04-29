"""Use case: conta Suggestions do workspace (default: status='Pendente')."""

from __future__ import annotations

from typing import Optional

from backend.app.application.base.errors import ValidationError
from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.models.suggestion import VALID_SUGGESTION_AGGREGATE_STATUSES
from backend.app.schemas.dto.suggestion import SuggestionCountResponse


async def count_suggestions(
    workspace_id: str,
    *,
    status: Optional[str] = "Pendente",
    repo: SuggestionRepositoryProtocol,
) -> SuggestionCountResponse:
    if status is not None and status not in VALID_SUGGESTION_AGGREGATE_STATUSES:
        raise ValidationError(
            f"status inválido: {status!r}; aceitos: {sorted(VALID_SUGGESTION_AGGREGATE_STATUSES)}",
            code="invalid_status_filter",
        )
    count = await repo.count_by_workspace(workspace_id, status=status)
    return SuggestionCountResponse(count=count, status=status)
