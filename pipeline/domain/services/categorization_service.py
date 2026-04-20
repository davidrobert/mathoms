"""CategorizationService — lógica pura de categorização por keywords (Fase 7 · R9/ISP).

Recebe :class:`CategorizationRules` (não ``StageConfig``). Keywords são
normalizados para uppercase na construção.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pipeline.domain.models.transaction import Transaction


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
    """Categoriza ``Transaction`` por match de keyword em ``description``.

    Função pura: ``categorize`` retorna uma nova lista — jamais muta as
    transações originais (usa ``dataclasses.replace``).
    """

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
