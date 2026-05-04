"""DTOs do aggregate ``Suggestion`` (ADR-153)."""

from backend.app.schemas.dto.suggestion.command import (
    AcceptSuggestionCommand,
    DismissSuggestionCommand,
    ModifySuggestionCommand,
    RegenerateSuggestionsCommand,
)
from backend.app.schemas.dto.suggestion.mapper import (
    brl_to_cents,
    cents_to_brl,
    suggestion_to_response,
)
from backend.app.schemas.dto.suggestion.response import (
    SuggestionCountResponse,
    SuggestionListResponse,
    SuggestionRegenerateResponse,
    SuggestionResponse,
    SuggestionsSummaryResponse,
)

__all__ = [
    "AcceptSuggestionCommand",
    "DismissSuggestionCommand",
    "ModifySuggestionCommand",
    "RegenerateSuggestionsCommand",
    "SuggestionCountResponse",
    "SuggestionListResponse",
    "SuggestionRegenerateResponse",
    "SuggestionResponse",
    "SuggestionsSummaryResponse",
    "brl_to_cents",
    "cents_to_brl",
    "suggestion_to_response",
]
