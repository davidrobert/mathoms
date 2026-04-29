"""Use case: modifica + aceita Suggestion → cria Decision com overrides (ADR-153).

Mesmo fluxo de :mod:`accept_suggestion`, mas o usuário customiza
``title``/``rationale``/``amount_brl`` antes da Decision ser criada.
Suggestion vai para status='Modificada' (não 'Aceita') para distinguir
no histórico.
"""

from __future__ import annotations

from backend.app.application.decisions._protocols import (
    DecisionRepositoryProtocol,
)
from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.application.suggestions.accept_suggestion import (
    _apply_acceptance,
    _create_decision_from,
    _load_pending,
)
from backend.app.schemas.dto.decision.mapper import cents_to_brl
from backend.app.schemas.dto.suggestion import (
    AcceptSuggestionCommand,
    ModifySuggestionCommand,
    SuggestionResponse,
    suggestion_to_response,
)


async def modify_suggestion(
    cmd: ModifySuggestionCommand,
    *,
    workspace_id: str,
    suggestion_id: str,
    suggestion_repo: SuggestionRepositoryProtocol,
    decision_repo: DecisionRepositoryProtocol,
    actor: str,
) -> SuggestionResponse:
    suggestion = await _load_pending(workspace_id, suggestion_id, suggestion_repo)
    final_amount = (
        cmd.amount_brl
        if cmd.amount_brl is not None
        else cents_to_brl(suggestion.amount_brl_cents)
    )
    accept_cmd = AcceptSuggestionCommand(
        decision_code=cmd.decision_code, note=cmd.note
    )
    decision = await _create_decision_from(
        suggestion,
        cmd=accept_cmd,
        amount_brl=final_amount,
        decision_repo=decision_repo,
        actor=actor,
        workspace_id=workspace_id,
        modified_title=cmd.title,
        modified_rationale=cmd.rationale,
    )
    _apply_acceptance(suggestion, decision_id=decision.id, target_status="Modificada")
    await suggestion_repo.add(suggestion)
    return suggestion_to_response(suggestion)
