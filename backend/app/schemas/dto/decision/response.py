"""Response DTOs do agregado ``Decision`` (ADR-136).

Money no wire como string decimal (``amount_brl``) — frontend renderiza
via ``<MonetaryValue/>``. Cents permanecem no DB; conversão acontece no
mapper.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DecisionResponse(BaseModel):
    """Decision projetada — o que a UI consome."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    code: str
    title: str
    rationale: Optional[str] = None
    amount_brl: Optional[Decimal] = None
    status: str
    supersedes_id: Optional[str] = None
    decided_at: Optional[date] = None
    executed_at: Optional[date] = None
    # ADR-162 — projection target (visível para UI mostrar "Atualiza Goal X").
    target_field: Optional[str] = None
    target_value: Optional[str] = None
    target_value_type: Optional[str] = None
    # ADR-163 — KPIs frozen do relatório-fonte da Suggestion.
    context_snapshot: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class DecisionListResponse(BaseModel):
    """Wrapper paginação-ready para ``GET /decisions``."""

    decisions: list[DecisionResponse]
    total: int
