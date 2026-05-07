"""Use case: atualiza campos editoriais da Decision + emite ``Updated``.

Status mudanças via /execute ou /supersede; aqui apenas reflete patch
direto e emite evento ``Updated`` (que pode incluir status se cmd inclui).
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.application.base.errors import NotFoundError
from backend.app.application.decisions._protocols import DecisionRepositoryProtocol
from backend.app.models.decision import Decision, DecisionEvent
from backend.app.schemas.dto.decision import (
    DecisionResponse,
    DecisionUpdateCommand,
    decision_to_response,
)
from backend.app.schemas.dto.decision.mapper import brl_to_cents


async def update_decision(
    cmd: DecisionUpdateCommand,
    *,
    workspace_id: str,
    decision_id: str,
    repo: DecisionRepositoryProtocol,
    actor: str,
) -> DecisionResponse:
    decision = await repo.get_by_id(workspace_id, decision_id)
    if decision is None:
        raise NotFoundError(f"Decision id={decision_id} não encontrada", code="decision_not_found")

    diff = _apply_patch(decision, cmd)
    decision.updated_at = datetime.now(timezone.utc)
    await repo.add(decision)  # flush UPDATE
    if diff:
        await _emit_updated_event(repo, decision, diff=diff, actor=actor)
    return decision_to_response(decision)


def _apply_patch(decision: Decision, cmd: DecisionUpdateCommand) -> dict:
    """Mutação in-place + retorna diff (campo → novo valor) para o evento."""
    diff: dict = {}
    if cmd.title is not None and cmd.title != decision.title:
        diff["title"] = cmd.title
        decision.title = cmd.title
    if cmd.rationale is not None and cmd.rationale != decision.rationale:
        diff["rationale"] = cmd.rationale
        decision.rationale = cmd.rationale
    if cmd.amount_brl is not None:
        new_cents = brl_to_cents(cmd.amount_brl)
        if new_cents != decision.amount_brl_cents:
            diff["amount_brl_cents"] = new_cents
            decision.amount_brl_cents = new_cents
    if cmd.status is not None and cmd.status != decision.status:
        diff["status"] = cmd.status
        decision.status = cmd.status
    if cmd.decided_at is not None and cmd.decided_at != decision.decided_at:
        diff["decided_at"] = cmd.decided_at.isoformat()
        decision.decided_at = cmd.decided_at
    # ADR-179 — quantificação de impacto + horizonte + prioridade.
    if cmd.impact_1y_brl is not None:
        new_cents_1y = brl_to_cents(cmd.impact_1y_brl)
        if new_cents_1y != decision.impact_1y_brl_cents:
            diff["impact_1y_brl_cents"] = new_cents_1y
            decision.impact_1y_brl_cents = new_cents_1y
    if cmd.impact_10y_brl is not None:
        new_cents_10y = brl_to_cents(cmd.impact_10y_brl)
        if new_cents_10y != decision.impact_10y_brl_cents:
            diff["impact_10y_brl_cents"] = new_cents_10y
            decision.impact_10y_brl_cents = new_cents_10y
    if cmd.horizon is not None and cmd.horizon != decision.horizon:
        diff["horizon"] = cmd.horizon
        decision.horizon = cmd.horizon
    if cmd.priority is not None and cmd.priority != decision.priority:
        diff["priority"] = cmd.priority
        decision.priority = cmd.priority
    return diff


async def _emit_updated_event(
    repo: DecisionRepositoryProtocol,
    decision: Decision,
    *,
    diff: dict,
    actor: str,
) -> None:
    event = DecisionEvent(
        decision_id=decision.id,
        event_type="Updated",
        actor=actor,
        payload={"diff": diff},
    )
    await repo.add_event(event)
