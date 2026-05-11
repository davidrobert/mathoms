"""Mappers ``CategorizationRule`` model ↔ DTO (ADR-186 §D3 · A12 P3 PR2)."""

from __future__ import annotations

from backend.app.models.categorization_rule import CategorizationRule
from backend.app.schemas.dto.categorization_rule import CategorizationRuleResponse


def rule_to_response(rule: CategorizationRule) -> CategorizationRuleResponse:
    """Model → DTO (Pydantic ``from_attributes`` faria isso, mas explicit é mais robusto)."""
    return CategorizationRuleResponse(
        id=rule.id,
        workspace_id=rule.workspace_id,
        keyword=rule.keyword,
        target_category=rule.target_category,
        priority=rule.priority,
        enabled=rule.enabled,
        origin_override_id=rule.origin_override_id,
        created_by_user_id=rule.created_by_user_id,
        applied_count=rule.applied_count,
        revert_count_manual_edit=rule.revert_count_manual_edit,
        revert_count_rule_disabled=rule.revert_count_rule_disabled,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )
