"""Use case: marca Decision como Executado + emite evento ``Executed``."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.decisions._protocols import DecisionRepositoryProtocol
from backend.app.models.decision import Decision, DecisionEvent
from backend.app.schemas.dto.decision import (
    DecisionExecuteCommand,
    DecisionResponse,
    decision_to_response,
)


async def mark_decision_executed(
    cmd: DecisionExecuteCommand,
    *,
    workspace_id: str,
    decision_id: str,
    repo: DecisionRepositoryProtocol,
    actor: str,
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
