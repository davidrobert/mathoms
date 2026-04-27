"""Use case: marca Decision antiga como Superseded por outra (nova).

Endpoint: ``POST /decisions/{old_id}/supersede`` com body
``{superseded_by_id: <new_id>}``. A nova ganha ``supersedes_id = old_id``;
a antiga vira ``status='Superseded'``. Ambos emitem evento ``Superseded``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.decisions._protocols import DecisionRepositoryProtocol
from backend.app.models.decision import Decision, DecisionEvent
from backend.app.schemas.dto.decision import (
    DecisionResponse,
    DecisionSupersedeCommand,
    decision_to_response,
)


async def supersede_decision(
    cmd: DecisionSupersedeCommand,
    *,
    workspace_id: str,
    old_decision_id: str,
    repo: DecisionRepositoryProtocol,
    actor: str,
) -> DecisionResponse:
    old, new = await _load_pair(repo, workspace_id, old_decision_id, cmd.superseded_by_id)
    _ensure_supersedable(old, new)
    _wire_supersede(old, new)
    await repo.add(old)
    await repo.add(new)
    await _emit_supersede_events(repo, old, new, note=cmd.note, actor=actor)
    return decision_to_response(old)


async def _load_pair(
    repo: DecisionRepositoryProtocol,
    workspace_id: str,
    old_id: str,
    new_id: str,
) -> tuple[Decision, Decision]:
    if old_id == new_id:
        raise ValidationError(
            "old e new não podem ser a mesma Decision", code="self_supersede"
        )
    old = await repo.get_by_id(workspace_id, old_id)
    if old is None:
        raise NotFoundError(
            f"Decision old id={old_id} não encontrada", code="decision_not_found"
        )
    new = await repo.get_by_id(workspace_id, new_id)
    if new is None:
        raise NotFoundError(
            f"Decision new id={new_id} não encontrada", code="decision_not_found"
        )
    return old, new


def _ensure_supersedable(old: Decision, new: Decision) -> None:
    if old.status == "Superseded":
        raise ValidationError(
            "Decision antiga já está Superseded", code="already_superseded"
        )
    if new.supersedes_id is not None:
        raise ValidationError(
            "Decision nova já tem supersedes_id", code="new_already_chained"
        )


def _wire_supersede(old: Decision, new: Decision) -> None:
    now = datetime.now(timezone.utc)
    old.status = "Superseded"
    old.updated_at = now
    new.supersedes_id = old.id
    new.updated_at = now


async def _emit_supersede_events(
    repo: DecisionRepositoryProtocol,
    old: Decision,
    new: Decision,
    *,
    note: Optional[str],
    actor: str,
) -> None:
    payload = {"old_id": old.id, "new_id": new.id, "note": note}
    await repo.add_event(
        DecisionEvent(
            decision_id=old.id, event_type="Superseded", actor=actor, payload=payload
        )
    )
    await repo.add_event(
        DecisionEvent(
            decision_id=new.id, event_type="Superseded", actor=actor, payload=payload
        )
    )
