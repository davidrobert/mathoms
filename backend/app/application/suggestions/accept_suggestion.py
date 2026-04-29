"""Use case: aceita Suggestion → cria Decision + transição de status (ADR-153).

Operação atômica em uma transaction:
    1. Carrega suggestion (validação tenancy + status pendente)
    2. Cria Decision via use case ``create_decision`` (ADR-136 — emite
       DecisionEvent ``Created`` com payload incluindo
       ``derived_from_suggestion_id`` para rastreabilidade)
    3. Atualiza suggestion: status='Aceita', accepted_decision_id=<novo>,
       accepted_at=now
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.decisions import create_decision
from backend.app.application.decisions._protocols import (
    DecisionRepositoryProtocol,
)
from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.models.decision import DecisionEvent
from backend.app.models.suggestion import Suggestion
from backend.app.schemas.dto.decision import DecisionCreateCommand
from backend.app.schemas.dto.decision.mapper import cents_to_brl
from backend.app.schemas.dto.suggestion import (
    AcceptSuggestionCommand,
    SuggestionResponse,
    suggestion_to_response,
)


async def accept_suggestion(
    cmd: AcceptSuggestionCommand,
    *,
    workspace_id: str,
    suggestion_id: str,
    suggestion_repo: SuggestionRepositoryProtocol,
    decision_repo: DecisionRepositoryProtocol,
    actor: str,
) -> SuggestionResponse:
    suggestion = await _load_pending(workspace_id, suggestion_id, suggestion_repo)
    decision = await _create_decision_from(
        suggestion,
        cmd=cmd,
        amount_brl=cents_to_brl(suggestion.amount_brl_cents),
        decision_repo=decision_repo,
        actor=actor,
        workspace_id=workspace_id,
        modified_title=None,
        modified_rationale=None,
    )
    _apply_acceptance(suggestion, decision_id=decision.id, target_status="Aceita")
    await suggestion_repo.add(suggestion)
    return suggestion_to_response(suggestion)


async def _load_pending(
    workspace_id: str,
    suggestion_id: str,
    repo: SuggestionRepositoryProtocol,
) -> Suggestion:
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
    return suggestion


async def _create_decision_from(
    suggestion: Suggestion,
    *,
    cmd: AcceptSuggestionCommand,
    amount_brl: Decimal | None,
    decision_repo: DecisionRepositoryProtocol,
    actor: str,
    workspace_id: str,
    modified_title: str | None,
    modified_rationale: str | None,
):
    """Cria Decision via use case canônico (ADR-136). Emite event extra
    com ``derived_from_suggestion_id`` para rastreabilidade."""
    title = modified_title if modified_title is not None else suggestion.title
    rationale = modified_rationale if modified_rationale is not None else suggestion.rationale
    decision_response = await create_decision(
        DecisionCreateCommand(
            code=cmd.decision_code,
            title=title,
            rationale=rationale,
            amount_brl=amount_brl,
            status="Pendente",
        ),
        workspace_id=workspace_id,
        repo=decision_repo,
        actor=actor,
    )
    # Evento extra registra a origem na Suggestion (rastreabilidade ADR-153).
    derivation_event = DecisionEvent(
        decision_id=decision_response.id,
        event_type="Updated",
        actor=actor,
        payload={
            "derivation": {
                "suggestion_id": suggestion.id,
                "kind": suggestion.kind,
                "section_id": suggestion.section_id,
                "report_id": suggestion.report_id,
                "modified": modified_title is not None or modified_rationale is not None,
                "note": cmd.note,
            }
        },
    )
    await decision_repo.add_event(derivation_event)
    return decision_response


def _apply_acceptance(
    suggestion: Suggestion,
    *,
    decision_id: str,
    target_status: str,
) -> None:
    suggestion.status = target_status
    suggestion.accepted_decision_id = decision_id
    suggestion.accepted_at = datetime.now(timezone.utc)
