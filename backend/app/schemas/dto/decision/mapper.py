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


# Atributos copiados 1:1 (sem conversão) de Decision para DecisionResponse.
# Money fields (cents → Decimal) e fields ADR-179 são tratados separadamente.
_DIRECT_FIELDS: tuple[str, ...] = (
    "id",
    "workspace_id",
    "code",
    "title",
    "rationale",
    "status",
    "supersedes_id",
    "decided_at",
    "executed_at",
    "target_field",
    "target_value",
    "target_value_type",
    "context_snapshot",
    "horizon",
    "priority",
    "created_at",
    "updated_at",
)


def decision_to_response(decision: Decision) -> DecisionResponse:
    """Decision row → DTO. Converte cents → Decimal BRL (ADR-090, ADR-179)."""
    return DecisionResponse(
        **{f: getattr(decision, f) for f in _DIRECT_FIELDS},
        amount_brl=cents_to_brl(decision.amount_brl_cents),
        impact_1y_brl=cents_to_brl(decision.impact_1y_brl_cents),
        impact_10y_brl=cents_to_brl(decision.impact_10y_brl_cents),
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
