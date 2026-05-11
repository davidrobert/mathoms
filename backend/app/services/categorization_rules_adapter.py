"""Adapter backend→pipeline para ``CategorizationRulesV2`` — cap 200 (ADR-186/188 §D5/D6)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.repositories.categorization_rule_repository import (
    CategorizationRuleRepository,
)
from pipeline.domain.services.categorization_service import (
    RULE_HARD_CAP,
    RULE_SOFT_CAP,
    CategorizationRulesV2,
    LearnedRule,
)

logger = get_logger("categorization.rules_adapter")


def _enforce_cap_and_warn(rows: list, workspace_id: str) -> list:
    """Hard cap + soft warning (caps em ``pipeline.domain.services.categorization_service`` · §D6)."""
    total = len(rows)
    if total >= RULE_HARD_CAP:
        logger.warning(
            "categorization.rules_adapter.cap_exceeded",
            extra={
                "workspace_id": workspace_id,
                "total_rules": total,
                "hard_cap": RULE_HARD_CAP,
            },
        )
        return rows[:RULE_HARD_CAP]
    if total >= RULE_SOFT_CAP:
        logger.info(
            "categorization.rules_adapter.approaching_cap",
            extra={"workspace_id": workspace_id, "total_rules": total},
        )
    return rows


def _row_to_learned(row) -> LearnedRule:
    """Keyword uppercase (paridade match substring E4)."""
    return LearnedRule(
        id=row.id,
        keyword=row.keyword.upper(),
        target_category=row.target_category,
        priority=row.priority,
        created_at=row.created_at,
    )


def load_categorization_rules_v2(
    *,
    workspace_id: str,
    db: Session,
    template_keywords: dict[str, tuple[str, ...]] | None = None,
) -> CategorizationRulesV2:
    """Constrói ``CategorizationRulesV2`` a partir do DB (cap N=200 aplicado)."""
    repo = CategorizationRuleRepository(db)
    rows = repo.list_for_workspace(workspace_id=workspace_id, enabled_only=True)
    rows = _enforce_cap_and_warn(rows, workspace_id)
    learned = tuple(_row_to_learned(row) for row in rows)
    return CategorizationRulesV2.from_template_and_learned(
        template_keywords=template_keywords or {},
        learned_rules=learned,
    )
