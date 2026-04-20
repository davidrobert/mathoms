"""Tests — ``pipeline.domain.models.Money`` (Fase 5.2)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import CURRENCY_PRECISION, Money  # noqa: E402


class TestConstructor:
    def test_accepts_decimal(self):
        m = Money(Decimal("10.00"), "BRL")
        assert m.amount == Decimal("10.00")

    def test_rejects_float(self):
        with pytest.raises(TypeError, match="Money.amount deve ser Decimal"):
            Money(0.1, "BRL")  # type: ignore[arg-type]

    def test_rejects_unknown_currency(self):
        with pytest.raises(ValueError, match="not registered" if False else "não registrada"):
            Money(Decimal("1"), "XYZ")


class TestFactory:
    def test_of_rejects_float(self):
        with pytest.raises(TypeError):
            Money.of(0.1, "BRL")

    def test_brl_quantizes_to_two_places(self):
        m = Money.brl("1.234")
        assert m.amount == Decimal("1.23")

    def test_jpy_has_zero_precision(self):
        m = Money.of("100.9", "JPY")
        assert m.amount == Decimal("101")

    def test_supports_integer(self):
        assert Money.brl(5).amount == Decimal("5.00")

    def test_zero(self):
        assert Money.zero("BRL") == Money.brl(0)


class TestArithmetic:
    def test_decimal_addition_precision(self):
        """Invariante principal: não há drift de float."""
        assert Money.brl("0.1") + Money.brl("0.2") == Money.brl("0.3")

    def test_addition_is_commutative(self):
        a = Money.brl("17.34")
        b = Money.brl("23.66")
        assert (a + b) == (b + a)

    def test_subtraction(self):
        a = Money.brl("50")
        b = Money.brl("20")
        assert a - b == Money.brl("30")

    def test_negation(self):
        assert -Money.brl("10") == Money.brl("-10")

    def test_multiplication_by_int(self):
        assert Money.brl("5") * 3 == Money.brl("15")

    def test_multiplication_by_float_rejected(self):
        with pytest.raises(TypeError):
            _ = Money.brl("5") * 1.5

    def test_cross_currency_raises(self):
        with pytest.raises(ValueError, match="Moedas incompatíveis"):
            _ = Money.brl("1") + Money.of("1", "USD")


class TestComparisons:
    def test_lt(self):
        assert Money.brl("1") < Money.brl("2")
        assert not (Money.brl("2") < Money.brl("2"))

    def test_le(self):
        assert Money.brl("2") <= Money.brl("2")

    def test_eq_based_on_amount_and_currency(self):
        assert Money.brl("5") == Money.brl("5")
        assert Money.brl("5") != Money.of("5", "USD")


class TestSerialization:
    def test_round_trip_dict(self):
        m = Money.brl("12.34")
        assert Money.from_dict(m.to_dict()) == m

    def test_to_float_loss_is_acknowledged(self):
        """``to_float`` é apenas para JSON legado — documentar o trade-off."""
        m = Money.brl("12.34")
        assert m.to_float() == 12.34


class TestPropertyBased:
    """Property tests simples — sem hypothesis para evitar dep extra."""

    def test_sum_of_identities_equals_self(self):
        values = ["1.00", "2.50", "3.75", "100", "0.01"]
        total = Money.brl("0")
        for v in values:
            total = total + Money.brl(v)
        expected = Money.brl("107.26")
        assert total == expected

    def test_currency_precision_registry(self):
        for cur, precision in CURRENCY_PRECISION.items():
            m = Money.of("1.23456789", cur)
            assert -m.amount.as_tuple().exponent == precision
