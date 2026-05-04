"""Mappers DB ↔ DTO do aggregate ``Decision`` (ADR-136).

Money: cents (BIGINT) ↔ Decimal BRL no wire. Centralizar aqui evita que
cada endpoint duplique a conversão.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from backend.app.models.decision import Decision, DecisionEvent
from backend.app.schemas.dto.decision.event import DecisionEventResponse
from backend.app.schemas.dto.decision.response import DecisionResponse


def cents_to_brl(cents: Optional[int]) -> Optional[Decimal]:
    """``None`` cents → ``None`` BRL. Senão, ``Decimal(cents) / 100``."""
    if cents is None:
        return None
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def brl_to_cents(brl: Optional[Decimal]) -> Optional[int]:
    """``None`` brl → ``None`` cents. Senão, ``int(round(brl * 100))``."""
    if brl is None:
        return None
    return int((Decimal(brl) * Decimal(100)).quantize(Decimal("1")))


def decision_to_response(decision: Decision) -> DecisionResponse:
    """Decision row → DTO. Converte cents → Decimal BRL no wire."""
    return DecisionResponse(
        id=decision.id,
        workspace_id=decision.workspace_id,
        code=decision.code,
        title=decision.title,
        rationale=decision.rationale,
        amount_brl=cents_to_brl(decision.amount_brl_cents),
        status=decision.status,
        supersedes_id=decision.supersedes_id,
        decided_at=decision.decided_at,
        executed_at=decision.executed_at,
        target_field=decision.target_field,
        target_value=decision.target_value,
        target_value_type=decision.target_value_type,
        context_snapshot=decision.context_snapshot,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )


def decision_event_to_response(event: DecisionEvent) -> DecisionEventResponse:
    return DecisionEventResponse(
        id=event.id,
        decision_id=event.decision_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        actor=event.actor,
        payload=event.payload or {},
    )
