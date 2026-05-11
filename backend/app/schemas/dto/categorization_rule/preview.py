"""Preview DTOs de ``CategorizationRule`` — POST /preview (ADR-186/188 · A12 P3 PR2)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RulePreviewRequest(BaseModel):
    """Input do preview — regra sintética + janela opcional de período."""

    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(..., min_length=1, max_length=255)
    target_category: str = Field(..., min_length=1, max_length=255)
    # ``(YYYYMM, YYYYMM)`` ou None (toda a base do workspace). Tuple em
    # JSON vira array; Pydantic v2 aceita.
    period_window: Optional[tuple[str, str]] = None


class WarningEntry(BaseModel):
    """Aviso não-bloqueante (UI mostra mas permite continuar)."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ConflictEntry(BaseModel):
    """Regra ativa do workspace que já usa essa keyword (UI alerta)."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    target_category: str
    priority: int


class RulePreviewResponse(BaseModel):
    """Shape rico para UI decidir antes de POST / (ADR-188 §D5)."""

    model_config = ConfigDict(extra="forbid")

    matches_total: int
    matches_in_closed_months: int
    matches_with_manual_override: int
    matches_blocked_internal_transfers: int
    matches_amount_total_brl_cents: int
    matches_by_month: dict[str, int]
    conflicts: list[ConflictEntry]
    low_risk: bool
    requires_user_confirmation: bool
    warnings: list[WarningEntry]
