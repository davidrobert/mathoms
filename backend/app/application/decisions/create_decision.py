"""Use case: cria Decision nova (status default ``Pendente``)."""

from __future__ import annotations

from backend.app.application.decisions._protocols import DecisionRepositoryProtocol
from backend.app.models.decision import Decision, DecisionEvent
from backend.app.schemas.dto.decision import (
    DecisionCreateCommand,
    DecisionResponse,
    decision_to_response,
)
from backend.app.schemas.dto.decision.mapper import brl_to_cents


async def create_decision(
    cmd: DecisionCreateCommand,
    *,
    workspace_id: str,
    repo: DecisionRepositoryProtocol,
    actor: str,
) -> DecisionResponse:
    """Cria Decision + emite ``DecisionCreatedEvent``.

    ADR-214: quando ``cmd.code`` é ``None``, server gera via
    ``repo.next_code(workspace_id)`` (advisory lock + ``MAX + 1``).
    Quando ``cmd.code`` é explícito (importer/migrator one-shot), respeita.
    ``UNIQUE (workspace_id, code)`` continua como defesa em profundidade.
    """
    code = cmd.code if cmd.code is not None else await repo.next_code(workspace_id)

    # ADR-179 — horizon tem default no model; só passa explícito se cmd
    # traz valor (Pydantic deixa None quando omitido).
    decision_kwargs: dict = {
        "workspace_id": workspace_id,
        "code": code,
        "title": cmd.title,
        "rationale": cmd.rationale,
        "amount_brl_cents": brl_to_cents(cmd.amount_brl),
        "status": cmd.status,
        "decided_at": cmd.decided_at,
        "target_field": cmd.target_field,
        "target_value": cmd.target_value,
        "target_value_type": cmd.target_value_type,
        "context_snapshot": cmd.context_snapshot,
        "impact_1y_brl_cents": brl_to_cents(cmd.impact_1y_brl),
        "impact_10y_brl_cents": brl_to_cents(cmd.impact_10y_brl),
        "priority": cmd.priority,
    }
    if cmd.horizon is not None:
        decision_kwargs["horizon"] = cmd.horizon
    decision = Decision(**decision_kwargs)
    added = await repo.add(decision)
    await _emit_created_event(repo, added, actor=actor)
    return decision_to_response(added)


# ADR-214: ConflictError("duplicate_code") removido — advisory lock +
# UNIQUE(workspace_id, code) garantem invariante por construção. Use case
# antigo fazia get_by_code antes do add (TOCTOU) — esse path morreu.


async def _emit_created_event(
    repo: DecisionRepositoryProtocol, decision: Decision, *, actor: str
) -> None:
    event = DecisionEvent(
        decision_id=decision.id,
        event_type="Created",
        actor=actor,
        payload={
            "code": decision.code,
            "title": decision.title,
            "status": decision.status,
            "amount_brl_cents": decision.amount_brl_cents,
        },
    )
    await repo.add_event(event)
