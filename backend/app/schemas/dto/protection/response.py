"""Response DTOs do aggregate `Protection` (ADR-192) — `policy_ref` mascarado."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProtectionResponse(BaseModel):
    """Apólice projetada — o que a UI consome."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    category: str
    holder_family_member_id: Optional[str] = None
    insurer: Optional[str] = None
    # Mascarado por default — só os últimos 4 chars (T05 expõe full via endpoint específico).
    policy_ref_masked: Optional[str] = None
    coverage_brl: Decimal
    premium_monthly_brl: Optional[Decimal] = None
    coverage_type: Optional[str] = None
    starts_at: date
    ends_at: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProtectionListResponse(BaseModel):
    """Wrapper paginação-ready para ``GET /protections``."""

    protections: list[ProtectionResponse]
    total: int
