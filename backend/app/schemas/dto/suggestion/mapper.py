"""Mappers DB ↔ DTO do aggregate ``Suggestion`` (ADR-153).

Money: cents (BIGINT) ↔ Decimal BRL no wire.
"""

from __future__ import annotations

from backend.app.models.suggestion import Suggestion
from backend.app.schemas.dto.decision.mapper import brl_to_cents, cents_to_brl
from backend.app.schemas.dto.suggestion.response import SuggestionResponse


def suggestion_to_response(suggestion: Suggestion) -> SuggestionResponse:
    return SuggestionResponse(
        id=suggestion.id,
        workspace_id=suggestion.workspace_id,
        report_id=suggestion.report_id,
        section_id=suggestion.section_id,
        kind=suggestion.kind,
        category=suggestion.category,
        origin=suggestion.origin,
        severity=suggestion.severity,
        title=suggestion.title,
        rationale=suggestion.rationale,
        amount_brl=cents_to_brl(suggestion.amount_brl_cents),
        status=suggestion.status,
        accepted_decision_id=suggestion.accepted_decision_id,
        dismissed_reason=suggestion.dismissed_reason,
        accepted_at=suggestion.accepted_at,
        dismissed_at=suggestion.dismissed_at,
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


__all__ = ["suggestion_to_response", "brl_to_cents", "cents_to_brl"]
