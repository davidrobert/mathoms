"""Tests — ``KeywordMatcher`` / ``find_longest_matching_keyword`` (Sessão A4a)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.keyword_matcher import (  # noqa: E402
    KeywordMatcher,
    find_longest_matching_keyword,
)


class TestSubstringMatch:
    def test_single_keyword_hits(self):
        cat, kw = find_longest_matching_keyword("MERCADO PAO", {"mercado": ["mercado"]})
        assert (cat, kw) == ("mercado", "MERCADO")

    def test_no_match_returns_none(self):
        cat, kw = find_longest_matching_keyword("qualquer coisa", {"m": ["xyz"]})
        assert (cat, kw) == (None, None)

    def test_normalizes_accents_and_case(self):
        cat, _ = find_longest_matching_keyword("PAGAMENTO FARMÁCIA", {"saude": ["farmacia"]})
        assert cat == "saude"


class TestLongestMatchWins:
    def test_longer_keyword_beats_shorter(self):
        rules = {
            "mercado_generico": ["mercado"],
            "pao_acucar": ["mercado pao"],
        }
        cat, kw = find_longest_matching_keyword("MERCADO PAO ACUCAR", rules)
        assert cat == "pao_acucar"
        assert kw == "MERCADO PAO"


class TestPrefixWildcard:
    def test_prefix_wildcard_matches_start(self):
        cat, _ = find_longest_matching_keyword("PIX RECEBIDO", {"pix": ["PIX*"]})
        assert cat == "pix"

    def test_prefix_wildcard_does_not_match_middle(self):
        cat, _ = find_longest_matching_keyword("COMPRA PIX RECEBIDO", {"pix": ["PIX*"]})
        assert cat is None


class TestSuffixWildcard:
    def test_suffix_wildcard_matches_end(self):
        cat, _ = find_longest_matching_keyword("PAGAMENTO BOLETO", {"bol": ["*BOLETO"]})
        assert cat == "bol"

    def test_suffix_wildcard_does_not_match_middle(self):
        cat, _ = find_longest_matching_keyword("BOLETO AGUA", {"bol": ["*BOLETO"]})
        assert cat is None


class TestEmptyInput:
    def test_empty_description_returns_none(self):
        cat, kw = find_longest_matching_keyword("", {"m": ["x"]})
        assert (cat, kw) == (None, None)

    def test_empty_rules_returns_none(self):
        cat, kw = find_longest_matching_keyword("anything", {})
        assert (cat, kw) == (None, None)


class TestKeywordMatcherClass:
    def test_match_returns_same_as_function(self):
        rules = {"mercado": ["mercado"]}
        m = KeywordMatcher(rules)
        assert m.match("MERCADO X") == find_longest_matching_keyword("MERCADO X", rules)

    def test_category_of_returns_only_category(self):
        m = KeywordMatcher({"x": ["foo"]})
        assert m.category_of("foo bar") == "x"
        assert m.category_of("nope") is None

    def test_none_rules_still_works(self):
        m = KeywordMatcher(None)
        assert m.category_of("anything") is None


class TestNormalizationWhitespaceCollapsing:
    def test_multiple_spaces_collapse_to_single(self):
        cat, _ = find_longest_matching_keyword(
            "MERCADO     PAO", {"pa": ["mercado pao"]}
        )
        assert cat == "pa"
