"""Response DTOs do aggregate ``Suggestion`` (ADR-153).

Money em wire como string decimal (``amount_brl``) — frontend renderiza
via ``<MonetaryValue/>``.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SuggestionResponse(BaseModel):
    """Sugestão projetada — o que a UI consome."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    report_id: Optional[str] = None
    section_id: str
    kind: str
    origin: str
    severity: str
    title: str
    rationale: str
    amount_brl: Optional[Decimal] = None
    status: str
    accepted_decision_id: Optional[str] = None
    dismissed_reason: Optional[str] = None
    accepted_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SuggestionListResponse(BaseModel):
    suggestions: list[SuggestionResponse]
    total: int


class SuggestionCountResponse(BaseModel):
    count: int
    status: Optional[str] = None


class SuggestionRegenerateResponse(BaseModel):
    """Resultado de uma regeneração — quantas drafts viraram persisted."""

    created: int
    skipped_dedup: int
    skipped_cap: int
    total_drafts: int
    suggestions: list[SuggestionResponse]
