"""CategorizationService + CategorizationRulesV2 (learning loop, ADR-186 §D5)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Mapping

from pipeline.domain.models.transaction import Transaction

# ADR-188 §D6 — Caps compartilhados entre adapter (P2) + endpoint (P3).
# Mantidos em ``pipeline/domain/services/`` (puro domínio, boundary-safe) para
# que backend e pipeline leiam do mesmo lugar — drift impossível.
# Override por workspace via ``workspaces.rule_cap_override`` (B2B2C consultor).
RULE_HARD_CAP: int = 200
RULE_SOFT_CAP: int = 50


@dataclass(frozen=True)
class CategorizationRules:
    """Mapping categoria → keywords (tuple para ser frozen-friendly)."""

    rules: dict[str, tuple[str, ...]]

    @classmethod
    def from_config(cls, categorization: dict) -> "CategorizationRules":
        compiled: dict[str, tuple[str, ...]] = {}
        for cat, keywords in (categorization or {}).items():
            if isinstance(keywords, dict):
                # suporte a estrutura `{categoria: {"keywords": [...]}}`
                flat = keywords.get("keywords") or []
            else:
                flat = keywords or []
            compiled[cat] = tuple(str(k).upper() for k in flat)
        return cls(rules=compiled)


class CategorizationService:
    """Categoriza ``Transaction`` por match de keyword (pure, retorna nova lista)."""

    def __init__(self, rules: CategorizationRules):
        self._rules = rules.rules

    def categorize(self, transactions: list[Transaction]) -> list[Transaction]:
        return [self._categorize_one(t) for t in transactions]

    def _categorize_one(self, t: Transaction) -> Transaction:
        desc = t.description.upper()
        for category, keywords in self._rules.items():
            if any(kw in desc for kw in keywords):
                return replace(t, category=category)
        return t


# =============================================================================
# ADR-186 A12.P2 — CategorizationRulesV2 (learned rules + template fallback)
# =============================================================================


@dataclass(frozen=True)
class LearnedRule:
    """Regra promovida (ADR-186 §D5). ``keyword`` já uppercase."""

    id: str
    keyword: str
    target_category: str
    priority: int
    created_at: datetime  # tz-aware


def _sort_key(rule: LearnedRule) -> tuple[int, int, datetime, str]:
    """Sort estável (priority desc, len(keyword) desc, created_at asc, id asc)."""
    return (-rule.priority, -len(rule.keyword), rule.created_at, rule.id)


@dataclass(frozen=True)
class CategorizationRulesV2:
    """Template + learned rules (ADR-186 §D5). ``learned_rules`` já ordenadas."""

    template_keywords: Mapping[str, tuple[str, ...]]
    learned_rules: tuple[LearnedRule, ...]

    @classmethod
    def from_template_and_learned(
        cls,
        template_keywords: Mapping[str, tuple[str, ...]] | None,
        learned_rules: tuple[LearnedRule, ...] | list[LearnedRule] | None,
    ) -> "CategorizationRulesV2":
        """Factory com sort estável (defensivo)."""
        sorted_learned = tuple(sorted(learned_rules or (), key=_sort_key))
        return cls(
            template_keywords=template_keywords or {},
            learned_rules=sorted_learned,
        )

    def match(self, narrative: str) -> tuple[str, str] | None:
        """``(target_category, rule_id)`` da 1ª regra que casa, senão ``None``."""
        if not self.learned_rules:
            return None
        narrative_upper = (narrative or "").upper()
        if not narrative_upper:
            return None
        for rule in self.learned_rules:
            if rule.keyword in narrative_upper:
                return (rule.target_category, rule.id)
        return None
