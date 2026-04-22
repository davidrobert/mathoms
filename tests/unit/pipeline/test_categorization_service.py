"""Tests — ``CategorizationService`` (Fase 7)."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import Money, Transaction  # noqa: E402
from pipeline.domain.services import CategorizationRules, CategorizationService  # noqa: E402


def _tx(desc: str, amount: str = "-10") -> Transaction:
    return Transaction(date(2026, 1, 5), desc, Money.brl(amount))


class TestRulesCompilation:
    def test_uppercases_keywords(self):
        rules = CategorizationRules.from_config({"Alimentacao": ["mercado", "Restaurante"]})
        assert rules.rules == {"Alimentacao": ("MERCADO", "RESTAURANTE")}

    def test_accepts_dict_structure(self):
        rules = CategorizationRules.from_config({"Transporte": {"keywords": ["uber", "99"]}})
        assert rules.rules == {"Transporte": ("UBER", "99")}

    def test_empty_config_yields_empty_rules(self):
        assert CategorizationRules.from_config({}).rules == {}


class TestCategorize:
    def _svc(self):
        return CategorizationService(
            CategorizationRules.from_config(
                {
                    "Alimentacao": ["mercado", "restaurante"],
                    "Transporte": ["uber", "99"],
                }
            )
        )

    def test_matches_by_keyword_case_insensitive(self):
        out = self._svc().categorize([_tx("MERCADO XYZ")])
        assert out[0].category == "Alimentacao"

    def test_matches_regardless_of_case_in_description(self):
        out = self._svc().categorize([_tx("mercado xyz")])
        assert out[0].category == "Alimentacao"

    def test_no_match_leaves_category_none(self):
        out = self._svc().categorize([_tx("PAGTO BOLETO")])
        assert out[0].category is None

    def test_first_match_wins(self):
        """Se a mesma descrição casar com duas regras, vence a primeira listada."""
        rules = CategorizationRules.from_config(
            {
                "RegraA": ["UBER"],
                "RegraB": ["UBER EATS"],  # mais específica, mas listada depois
            }
        )
        out = CategorizationService(rules).categorize([_tx("UBER EATS")])
        assert out[0].category == "RegraA"

    def test_does_not_mutate_original(self):
        originals = [_tx("MERCADO")]
        svc = self._svc()
        result = svc.categorize(originals)
        assert originals[0].category is None  # inalterado
        assert result[0].category == "Alimentacao"

    def test_returns_same_length(self):
        inputs = [_tx("A"), _tx("B"), _tx("C")]
        out = self._svc().categorize(inputs)
        assert len(out) == len(inputs)

    def test_frozen_transaction_unmutated(self):
        """``with_category`` é o único caminho para setar — frozen não aceita =."""
        t = _tx("X")
        with pytest.raises(FrozenInstanceError):
            t.category = "foo"  # type: ignore[misc]


class TestPropertyLikeInvariants:
    def test_fields_preserved_except_category(self):
        rules = CategorizationRules.from_config({"X": ["X"]})
        svc = CategorizationService(rules)
        inputs = [_tx("X"), _tx("Y", amount="-30")]
        out = svc.categorize(inputs)
        for orig, cat in zip(inputs, out):
            assert cat.date == orig.date
            assert cat.amount == orig.amount
            assert cat.description == orig.description
            assert cat.member_key == orig.member_key
