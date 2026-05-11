"""Adapter backend→pipeline para ``CategorizationRulesV2`` — cap 200 (ADR-186 §D5)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.repositories.categorization_rule_repository import (
    CategorizationRuleRepository,
)
from pipeline.domain.services.categorization_service import (
    CategorizationRulesV2,
    LearnedRule,
)

logger = get_logger("categorization.rules_adapter")

# ADR-186 §"Hard limit MVP" — soft warning ≥50, hard cap 200.
_SOFT_WARN_THRESHOLD = 50
_HARD_CAP = 200


def _enforce_cap_and_warn(rows: list, workspace_id: str) -> list:
    """Hard cap N=200 + soft warning ≥50 (ADR-186)."""
    total = len(rows)
    if total >= _HARD_CAP:
        logger.warning(
            "categorization.rules_adapter.cap_exceeded",
            extra={
                "workspace_id": workspace_id,
                "total_rules": total,
                "hard_cap": _HARD_CAP,
            },
        )
        return rows[:_HARD_CAP]
    if total >= _SOFT_WARN_THRESHOLD:
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
