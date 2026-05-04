"""Use cases do aggregate ``Suggestion`` (ADR-101 R15 · ADR-153)."""

from backend.app.application.suggestions.accept_suggestion import accept_suggestion
from backend.app.application.suggestions.count_suggestions import count_suggestions
from backend.app.application.suggestions.dismiss_suggestion import dismiss_suggestion
from backend.app.application.suggestions.get_suggestion import get_suggestion
from backend.app.application.suggestions.list_suggestions import list_suggestions
from backend.app.application.suggestions.modify_suggestion import modify_suggestion
from backend.app.application.suggestions.regenerate_for_report import (
    regenerate_for_report,
)
from backend.app.application.suggestions.summary import get_pending_summary

__all__ = [
    "accept_suggestion",
    "count_suggestions",
    "dismiss_suggestion",
    "get_pending_summary",
    "get_suggestion",
    "list_suggestions",
    "modify_suggestion",
    "regenerate_for_report",
]
