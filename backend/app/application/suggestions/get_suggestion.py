"""Use case: retorna uma Suggestion pelo id."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.schemas.dto.suggestion import (
    SuggestionResponse,
    suggestion_to_response,
)


async def get_suggestion(
    workspace_id: str,
    suggestion_id: str,
    *,
    repo: SuggestionRepositoryProtocol,
) -> SuggestionResponse:
    suggestion = await repo.get_by_id(workspace_id, suggestion_id)
    if suggestion is None:
        raise NotFoundError(
            f"Suggestion id={suggestion_id} não encontrada no workspace",
            code="suggestion_not_found",
        )
    return suggestion_to_response(suggestion)
