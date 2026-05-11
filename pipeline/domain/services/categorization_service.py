"""CategorizationService + CategorizationRulesV2 (learning loop, ADR-186 §D5)."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable, Mapping, Protocol, TypeVar

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


class _RuleSortable(Protocol):
    """Protocol mínimo p/ ``sort_rules_canonical`` — vale para ``LearnedRule``
    *e* SQLAlchemy ``CategorizationRule`` (ADR-188 §5 risco #3)."""

    @property
    def priority(self) -> int: ...

    @property
    def keyword(self) -> str: ...

    @property
    def created_at(self) -> datetime: ...

    @property
    def id(self) -> str: ...


_R = TypeVar("_R", bound=_RuleSortable)


def _sort_key(rule: _RuleSortable) -> tuple[int, int, datetime, str]:
    """Sort estável shared adapter P2 ↔ services P3 (ADR-188 §5 #3)."""
    return (-rule.priority, -len(rule.keyword), rule.created_at, rule.id)


def sort_rules_canonical(rules: Iterable[_R]) -> tuple[_R, ...]:
    """Único helper de sort — aceita LearnedRule + ORM CategorizationRule (ADR-188 §5 #3)."""
    return tuple(sorted(rules or (), key=_sort_key))


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
        """Factory com sort canônico (defensivo)."""
        sorted_learned = sort_rules_canonical(learned_rules or ())
        return cls(
            template_keywords=template_keywords or {},
            learned_rules=sorted_learned,
        )

    def match(self, narrative: str) -> tuple[str, str] | None:
        """``(target_category, rule_id)`` da 1ª regra que casa, senão ``None``."""
        return self.match_normalized(normalize_narrative(narrative))

    def match_normalized(self, narrative_upper: str) -> tuple[str, str] | None:
        """Match com narrative já uppercase — perf R1 (cache ``.upper()`` no caller); opt-in Aho-Corasick via env."""
        if not self.learned_rules or not narrative_upper:
            return None
        if _aho_corasick_enabled() and len(self.learned_rules) > _AC_RULE_COUNT_THRESHOLD:
            result = match_normalized_aho_corasick(narrative_upper, self.learned_rules)
            if result is not None:
                return result
            # Caso lib ausente: fallback silencioso para loop linear abaixo.
        for rule in self.learned_rules:
            if rule.keyword in narrative_upper:
                return (rule.target_category, rule.id)
        return None


_AC_RULE_COUNT_THRESHOLD: int = 50


def _aho_corasick_enabled() -> bool:
    """``True`` se ``MATHOMS_RULE_MATCH_AHO_CORASICK=1`` — default off, lido por-request (ADR-111)."""
    return os.environ.get("MATHOMS_RULE_MATCH_AHO_CORASICK") == "1"


def normalize_narrative(narrative: str) -> str:
    """Normaliza narrativa (uppercase) — pure helper compartilhado adapter/preview/apply (PR3 R1)."""
    return (narrative or "").upper()


# =============================================================================
# ADR-188 PR3 — Aho-Corasick automaton opcional (feature-flagged)
# =============================================================================


def _try_build_aho_corasick(keywords: tuple[str, ...]):
    """Tenta construir automaton ``pyahocorasick`` — ``None`` se lib ausente; build por-request (ADR-111)."""
    try:
        import ahocorasick  # type: ignore[import-not-found]
    except ImportError:
        return None
    if not keywords:
        return None
    automaton = ahocorasick.Automaton()
    for idx, kw in enumerate(keywords):
        automaton.add_word(kw, (idx, kw))
    automaton.make_automaton()
    return automaton


def _match_with_aho_corasick(
    automaton,
    narrative_upper: str,
    rules: tuple[LearnedRule, ...],
    keyword_to_rules: dict[str, list[int]],
) -> tuple[str, str] | None:
    """Acha primeiro match canônico — mantém sort ordering das regras."""
    if not narrative_upper:
        return None
    matched_keywords: set[str] = set()
    for _, (_, kw) in automaton.iter(narrative_upper):
        matched_keywords.add(kw)
    if not matched_keywords:
        return None
    # Itera regras (já ordenadas canonicamente) e devolve a 1ª cujo keyword
    # apareceu no automaton — preserva sort: priority/len/created_at/id.
    for rule in rules:
        if rule.keyword in matched_keywords:
            return (rule.target_category, rule.id)
    return None


def match_normalized_aho_corasick(
    narrative_upper: str,
    rules: tuple[LearnedRule, ...],
) -> tuple[str, str] | None:
    """Match via Aho-Corasick automaton — ``None`` se lib ausente; caller faz fallback."""
    if not rules or not narrative_upper:
        return None
    keywords = tuple(rule.keyword for rule in rules)
    automaton = _try_build_aho_corasick(keywords)
    if automaton is None:
        return None
    # ``keyword_to_rules`` reservado para futura paralelização (passa para
    # _match_with_aho_corasick mas não é usado no fluxo single-shot atual).
    return _match_with_aho_corasick(automaton, narrative_upper, rules, {})
