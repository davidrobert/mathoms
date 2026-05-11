"""DTOs do agregado ``CategorizationRule`` (ADR-186 §D3 · A12 P1/P3)."""

from backend.app.schemas.dto.categorization_rule.command import (
    CategorizationRuleCreate,
)
from backend.app.schemas.dto.categorization_rule.list_response import (
    RulesListMeta,
    RulesListResponse,
)
from backend.app.schemas.dto.categorization_rule.preview import (
    ConflictEntry,
    RulePreviewRequest,
    RulePreviewResponse,
    WarningEntry,
)
from backend.app.schemas.dto.categorization_rule.response import (
    CategorizationRuleResponse,
)

__all__ = [
    "CategorizationRuleCreate",
    "CategorizationRuleResponse",
    "ConflictEntry",
    "RulePreviewRequest",
    "RulePreviewResponse",
    "RulesListMeta",
    "RulesListResponse",
    "WarningEntry",
]
