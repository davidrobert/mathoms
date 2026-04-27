"""Use case: cria Decision nova (status default ``Pendente``)."""

from __future__ import annotations

from backend.app.application.base.errors import ConflictError
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
    """Cria Decision + emite ``DecisionCreatedEvent``. Conflito por code."""
    existing = await repo.get_by_code(workspace_id, cmd.code)
    if existing is not None:
        raise ConflictError(
            f"Decision com code={cmd.code!r} já existe no workspace",
            code="duplicate_code",
        )

    decision = Decision(
        workspace_id=workspace_id,
        code=cmd.code,
        title=cmd.title,
        rationale=cmd.rationale,
        amount_brl_cents=brl_to_cents(cmd.amount_brl),
        status=cmd.status,
        decided_at=cmd.decided_at,
    )
    added = await repo.add(decision)
    await _emit_created_event(repo, added, actor=actor)
    return decision_to_response(added)


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
