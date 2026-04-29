"""Use case: descarta Suggestion com motivo (ADR-153)."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.schemas.dto.suggestion import (
    DismissSuggestionCommand,
    SuggestionResponse,
    suggestion_to_response,
)


async def dismiss_suggestion(
    cmd: DismissSuggestionCommand,
    *,
    workspace_id: str,
    suggestion_id: str,
    repo: SuggestionRepositoryProtocol,
) -> SuggestionResponse:
    suggestion = await repo.get_by_id(workspace_id, suggestion_id)
    if suggestion is None:
        raise NotFoundError(
            f"Suggestion id={suggestion_id} não encontrada no workspace",
            code="suggestion_not_found",
        )
    if suggestion.status != "Pendente":
        raise ConflictError(
            f"Suggestion id={suggestion_id} já está em status={suggestion.status!r}; "
            f"transição só é permitida de Pendente",
            code="suggestion_not_pending",
        )
    suggestion.status = "Descartada"
    suggestion.dismissed_reason = cmd.reason
    suggestion.dismissed_at = datetime.now(timezone.utc)
    await repo.add(suggestion)
    return suggestion_to_response(suggestion)
