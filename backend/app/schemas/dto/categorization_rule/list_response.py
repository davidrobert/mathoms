"""List DTO de ``CategorizationRule`` — GET / com ``meta.warnings`` (ADR-188 §D6 · A12 P3 PR2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.dto.categorization_rule.preview import WarningEntry
from backend.app.schemas.dto.categorization_rule.response import (
    CategorizationRuleResponse,
)


class RulesListMeta(BaseModel):
    """Metadados de paginação + caps (ADR-188 §D6)."""

    model_config = ConfigDict(extra="forbid")

    count: int
    soft_cap: int
    hard_cap: int
    warnings: list[WarningEntry]


class RulesListResponse(BaseModel):
    """Lista paginada de regras + meta."""

    model_config = ConfigDict(extra="forbid")

    rules: list[CategorizationRuleResponse]
    meta: RulesListMeta
