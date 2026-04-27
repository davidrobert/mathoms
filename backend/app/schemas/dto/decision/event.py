"""DecisionEvent DTOs (ADR-136 — append-only audit trail)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DecisionEventResponse(BaseModel):
    """Evento append-only do log de auditoria do aggregate."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    decision_id: str
    event_type: str
    occurred_at: datetime
    actor: str
    payload: dict
