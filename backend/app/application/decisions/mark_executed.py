"""Use case: marca Decision como Executado + emite evento ``Executed``.

ADR-162 — quando a Decision tem `target_field` populado, dispara
``project_decision_to_goal`` na mesma transação. Falha de projection
propaga ValidationError e aborta a transição.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.decisions._protocols import DecisionRepositoryProtocol
from backend.app.models.decision import Decision, DecisionEvent
from backend.app.schemas.dto.decision import (
    DecisionExecuteCommand,
    DecisionResponse,
    decision_to_response,
)
from backend.app.services.decision_goal_projection import project_decision_to_goal


async def mark_decision_executed(
    cmd: DecisionExecuteCommand,
    *,
    workspace_id: str,
    decision_id: str,
    repo: DecisionRepositoryProtocol,
    actor: str,
    db: AsyncSession | None = None,
) -> DecisionResponse:
    decision = await repo.get_by_id(workspace_id, decision_id)
    if decision is None:
        raise NotFoundError(f"Decision id={decision_id} não encontrada", code="decision_not_found")
    _ensure_executable(decision)

    executed_on = cmd.executed_at or date.today()
    decision.status = "Executado"
    decision.executed_at = executed_on
    decision.updated_at = datetime.now(timezone.utc)
    await repo.add(decision)
    await _emit_executed_event(repo, decision, note=cmd.note, actor=actor)
    if decision.target_field is not None and db is not None:
        new_goal = await project_decision_to_goal(decision, db=db, actor=actor)
        if new_goal is not None:
            await _emit_goal_projected_event(repo, decision, goal_id=new_goal.id, actor=actor)
    return decision_to_response(decision)


def _ensure_executable(decision: Decision) -> None:
    if decision.status in {"Executado", "Descartado", "Superseded"}:
        raise ValidationError(
            f"Decision em status {decision.status!r} não pode ser executada",
            code="invalid_transition",
        )


async def _emit_executed_event(
    repo: DecisionRepositoryProtocol,
    decision: Decision,
    *,
    note: Optional[str],
    actor: str,
) -> None:
    event = DecisionEvent(
        decision_id=decision.id,
        event_type="Executed",
        actor=actor,
        payload={
            "executed_at": decision.executed_at.isoformat() if decision.executed_at else None,
            "note": note,
        },
    )
    await repo.add_event(event)


async def _emit_goal_projected_event(
    repo: DecisionRepositoryProtocol,
    decision: Decision,
    *,
    goal_id: str,
    actor: str,
) -> None:
    """Audit trail da projection (ADR-162) — qual Goal version foi criada."""
    event = DecisionEvent(
        decision_id=decision.id,
        event_type="GoalProjected",
        actor=actor,
        payload={
            "target_field": decision.target_field,
            "target_value": decision.target_value,
            "target_value_type": decision.target_value_type,
            "goal_id": goal_id,
        },
    )
    await repo.add_event(event)
