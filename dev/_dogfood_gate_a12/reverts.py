"""Revert simulation: ~20% override 'rule' → 'manual' divergente."""

from __future__ import annotations

from sqlalchemy import select

from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    OVERRIDE_SOURCE_RULE,
    TransactionOverride,
)
from dev._dogfood_gate_a12.fixture import RNG
from dev._dogfood_gate_a12.rule_ops import sync_db_ctx


def _select_rule_overrides(sync_db, ws_id: str) -> list[TransactionOverride]:
    return list(
        sync_db.execute(
            select(TransactionOverride).where(
                TransactionOverride.workspace_id == ws_id,
                TransactionOverride.source == OVERRIDE_SOURCE_RULE,
                TransactionOverride.deleted_at.is_(None),
            )
        )
        .scalars()
        .all()
    )


def _revert_override(ovr: TransactionOverride) -> str | None:
    ovr.source = OVERRIDE_SOURCE_MANUAL
    ovr.new_category = "Revertido Pelo Usuario"
    return ovr.rule_id


def _bump_revert_counts(sync_db, revert_per_rule: dict[str, int]) -> None:
    for rule_id, n in revert_per_rule.items():
        rule = sync_db.get(CategorizationRule, rule_id)
        if rule:
            rule.revert_count_manual_edit = (rule.revert_count_manual_edit or 0) + n


def _sample_size(total: int, fraction: float) -> int:
    return max(1, int(total * fraction))


def simulate_reverts(ws_id: str, *, fraction: float = 0.2) -> dict[str, int]:
    """Reverte ``fraction`` overrides + bump revert_count_manual_edit."""
    revert_per_rule: dict[str, int] = {}
    with sync_db_ctx() as sync_db:
        rows = _select_rule_overrides(sync_db, ws_id)
        if not rows:
            return revert_per_rule
        k = _sample_size(len(rows), fraction)
        for ovr in RNG.sample(rows, min(k, len(rows))):
            rule_id = _revert_override(ovr)
            if rule_id:
                revert_per_rule[rule_id] = revert_per_rule.get(rule_id, 0) + 1
        _bump_revert_counts(sync_db, revert_per_rule)
        sync_db.commit()
    return revert_per_rule


__all__ = ["simulate_reverts"]
