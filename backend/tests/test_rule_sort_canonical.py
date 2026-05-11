"""Property-based tests do ``sort_rules_canonical`` — zero drift adapter P2 vs services P3 (ADR-188 PR3 R3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.models.categorization_rule import CategorizationRule
from pipeline.domain.services.categorization_service import (
    LearnedRule,
    sort_rules_canonical,
)


def _learned(*, id: str, keyword: str, priority: int, created_at: datetime) -> LearnedRule:
    return LearnedRule(
        id=id,
        keyword=keyword,
        target_category="X",
        priority=priority,
        created_at=created_at,
    )


def _orm(*, id: str, keyword: str, priority: int, created_at: datetime) -> CategorizationRule:
    """ORM model — testa que protocol aceita ambos os tipos."""
    return CategorizationRule(
        id=id,
        workspace_id="ws1",
        keyword=keyword,
        target_category="X",
        priority=priority,
        created_at=created_at,
    )


_BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_priority_desc_first():
    rules = [
        _learned(id="b", keyword="UBER", priority=50, created_at=_BASE),
        _learned(id="a", keyword="UBER", priority=100, created_at=_BASE),
    ]
    sorted_rules = sort_rules_canonical(rules)
    assert [r.id for r in sorted_rules] == ["a", "b"]


def test_len_keyword_desc_when_priority_equal():
    rules = [
        _learned(id="short", keyword="UBE", priority=100, created_at=_BASE),
        _learned(id="long", keyword="UBEREATS", priority=100, created_at=_BASE),
    ]
    sorted_rules = sort_rules_canonical(rules)
    assert [r.id for r in sorted_rules] == ["long", "short"]


def test_created_at_asc_when_priority_and_len_equal():
    rules = [
        _learned(id="newer", keyword="UBER", priority=100, created_at=_BASE + timedelta(days=1)),
        _learned(id="older", keyword="UBER", priority=100, created_at=_BASE),
    ]
    sorted_rules = sort_rules_canonical(rules)
    assert [r.id for r in sorted_rules] == ["older", "newer"]


def test_id_asc_when_all_other_fields_equal():
    rules = [
        _learned(id="zzz", keyword="UBER", priority=100, created_at=_BASE),
        _learned(id="aaa", keyword="UBER", priority=100, created_at=_BASE),
    ]
    sorted_rules = sort_rules_canonical(rules)
    assert [r.id for r in sorted_rules] == ["aaa", "zzz"]


def test_orm_model_works_via_protocol():
    """Mesmo helper aceita SQLAlchemy ``CategorizationRule`` (protocol-based)."""
    rules = [
        _orm(id="b", keyword="UBE", priority=100, created_at=_BASE),
        _orm(id="a", keyword="UBEREATS", priority=100, created_at=_BASE),
    ]
    sorted_rules = sort_rules_canonical(rules)
    assert [r.id for r in sorted_rules] == ["a", "b"]


def test_empty_input_returns_empty_tuple():
    assert sort_rules_canonical([]) == ()


def test_none_input_returns_empty_tuple():
    assert sort_rules_canonical(None) == ()  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "ids,expected_winner",
    [
        # priority dominates len
        (
            [("a", "UBE", 200, 0), ("b", "UBEREATS", 100, 0)],
            "a",
        ),
        # len dominates created_at
        (
            [("a", "UBE", 100, 1), ("b", "UBEREATS", 100, 5)],
            "b",
        ),
        # created_at dominates id
        (
            [("zzz", "UBER", 100, 5), ("aaa", "UBER", 100, 1)],
            "aaa",
        ),
    ],
)
def test_tiebreaker_precedence(ids, expected_winner):
    rules = [
        _learned(id=i, keyword=k, priority=p, created_at=_BASE + timedelta(days=d))
        for i, k, p, d in ids
    ]
    sorted_rules = sort_rules_canonical(rules)
    assert sorted_rules[0].id == expected_winner
