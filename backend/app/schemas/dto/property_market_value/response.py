"""Response DTOs de ``PropertyMarketValue``."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

PmvSource = Literal[
    "user_declared",
    "avaliacao_terceiros",
    "cep_proxy_futuro",
]


class PropertyMarketValueResponse(BaseModel):
    """Declaração persistida (com cents convertidos para BRL Decimal)."""

    id: str = Field(..., max_length=36)
    property_id: str = Field(..., max_length=36)
    workspace_id: str = Field(..., max_length=36)
    valor_brl: Decimal = Field(..., gt=0)
    valuation_date: date
    source: PmvSource
    confidence: Optional[Decimal] = None
    notes: Optional[str] = None
    superseded_by_id: Optional[str] = Field(None, max_length=36)
    created_at: datetime
    created_by_user_id: Optional[str] = Field(None, max_length=36)

    model_config = {"from_attributes": True}
