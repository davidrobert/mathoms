"""Command DTOs de ``CategorizationRule`` — input de POST rules (ADR-186 §D3 · A12 P3)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Bounds intencionalmente largos para suportar promoção administrativa
# futura (regras "carimbadas" pelo time de produto). UI clamp em 1..200.
_PRIORITY_MIN: int = 1
_PRIORITY_MAX: int = 1000
_PRIORITY_DEFAULT: int = 100


class CategorizationRuleCreate(BaseModel):
    """Cria nova ``CategorizationRule`` (origem: promoção de override)."""

    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(..., min_length=2, max_length=255)
    target_category: str = Field(..., min_length=1, max_length=255)
    priority: int = Field(
        _PRIORITY_DEFAULT,
        ge=_PRIORITY_MIN,
        le=_PRIORITY_MAX,
        description="Prioridade de match (maior ganha; default 100).",
    )
    origin_override_id: Optional[str] = Field(
        None,
        min_length=36,
        max_length=36,
        description="ID do TransactionOverride que originou esta regra (auditoria).",
    )
    confirmed_visualized_months_impact: bool = Field(
        False,
        description=(
            "Placeholder P4 — UI confirma impacto em meses visualizados. "
            "Mantido em PR2 para não breaking change quando P4 ligar."
        ),
    )
