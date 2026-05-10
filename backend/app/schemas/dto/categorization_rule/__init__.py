"""DTOs do agregado ``CategorizationRule`` (ADR-186 §D3 · A12 P1)."""

from backend.app.schemas.dto.categorization_rule.command import (
    CategorizationRuleCreate,
)
from backend.app.schemas.dto.categorization_rule.response import (
    CategorizationRuleResponse,
)

__all__ = [
    "CategorizationRuleCreate",
    "CategorizationRuleResponse",
]
