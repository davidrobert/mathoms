"""Response DTOs do agregado ``Risk`` (ADR-178).

Money no wire em string decimal (``impact_brl``). Cents permanecem no DB;
mapper centraliza conversão.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RiskResponse(BaseModel):
    """Risk projetado — o que a UI consome."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    code: str
    name: str
    rationale: str
    probability: Optional[str] = None
    impact_level: str
    impact_brl: Optional[Decimal] = None
    status: str
    mitigations_decision_ids: list[str]
    created_at: datetime
    updated_at: datetime


class RiskListResponse(BaseModel):
    """Wrapper paginação-ready para ``GET /risks``."""

    risks: list[RiskResponse]
    total: int
