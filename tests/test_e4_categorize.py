#!/usr/bin/env python3
"""Tests for E4 categorization functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.categorize_transactions import (
    categorize_expense,
    categorize_income,
    find_longest_matching_keyword,
    is_internal_transfer,
    normalize_text,
)


class TestNormalizeText:
    def test_uppercase(self):
        assert normalize_text("hello") == "HELLO"

    def test_remove_accents(self):
        result = normalize_text("débito crédito são")
        assert "É" not in result
        assert "Ã" not in result
        assert "DEBITO" in result

    def test_collapse_whitespace(self):
        assert normalize_text("  hello   world  ") == "HELLO WORLD"

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_none_like(self):
        assert normalize_text(None) == ""


class TestFindLongestMatchingKeyword:
    def test_finds_longest_match(self):
        keywords = {
            "alimentacao": ["SUPERMERCADO", "SUPERMERCADO EXTRA"],
            "transporte": ["UBER"],
        }
        category, matched = find_longest_matching_keyword("SUPERMERCADO EXTRA SP", keywords)
        assert category == "alimentacao"
        assert matched is not None
        assert "SUPERMERCADO EXTRA" in matched

    def test_no_match(self):
        keywords = {"alimentacao": ["SUPERMERCADO"]}
        category, matched = find_longest_matching_keyword("NETFLIX MONTHLY", keywords)
        assert category is None
        assert matched is None

    def test_wildcard_start(self):
        keywords = {"moradia": ["*ALUGUEL"]}
        category, _ = find_longest_matching_keyword("PAGAMENTO ALUGUEL", keywords)
        assert category == "moradia"

    def test_wildcard_end(self):
        keywords = {"moradia": ["ALUGUEL*"]}
        category, _ = find_longest_matching_keyword("ALUGUEL JANEIRO", keywords)
        assert category == "moradia"


class TestIsInternalTransfer:
    def test_non_transfer(self):
        assert is_internal_transfer("SUPERMERCADO EXTRA") is False

    def test_returns_bool(self):
        result = is_internal_transfer("SOMETHING")
        assert isinstance(result, bool)


class TestCategorizeIncome:
    def test_returns_string_or_none(self):
        result = categorize_income("RANDOM CREDIT")
        assert result is None or isinstance(result, str)


class TestCategorizeExpense:
    def test_returns_string_or_none(self):
        result = categorize_expense("RANDOM DEBIT")
        assert result is None or isinstance(result, str)

    def test_empty_description(self):
        """Entrada vazia não deve levantar (7D.1)."""
        r = categorize_expense("")
        assert r is None or isinstance(r, str)
