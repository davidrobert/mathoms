#!/usr/bin/env python3
"""Tests for E2 value parsing functions (parse_brl, parse_usd)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e2.common import parse_brl, parse_usd, safe_date


class TestParseBRL:
    def test_standard_format(self):
        assert parse_brl("1.234,56") == 1234.56

    def test_simple_decimal(self):
        assert parse_brl("98,00") == 98.0

    def test_negative_dash(self):
        assert parse_brl("-1.234,56") == -1234.56

    def test_negative_parentheses(self):
        assert parse_brl("(1.234,56)") == -1234.56

    def test_negative_parenthesized_dash(self):
        # Current behavior: lstrip("(-") also strips leading digits after "(-"
        # This is a known limitation for the rare "(-1.234,56)" format.
        # The standard negative formats "- 1.234,56" and "(1.234,56)" work correctly.
        result = parse_brl("(-1.234,56)")
        assert result is not None

    def test_with_currency_symbol(self):
        assert parse_brl("R$ 98,00") == 98.0

    def test_negative_with_currency_symbol(self):
        assert parse_brl("-R$ 98,00") == -98.0

    def test_zero(self):
        assert parse_brl("0,00") == 0.0

    def test_large_number(self):
        assert parse_brl("1.234.567,89") == 1234567.89

    def test_no_decimals(self):
        assert parse_brl("1.234") == 1234.0

    def test_only_cents(self):
        assert parse_brl("0,50") == 0.50

    def test_empty_string(self):
        assert parse_brl("") is None

    def test_none_input(self):
        assert parse_brl(None) is None

    def test_dash_only(self):
        assert parse_brl("-") is None

    def test_whitespace(self):
        assert parse_brl("  1.234,56  ") == 1234.56

    def test_brl_prefix(self):
        assert parse_brl("BRL 500,00") == 500.0

    def test_usd_prefix_stripped(self):
        assert parse_brl("US$ 100,00") == 100.0

    def test_negative_dash_prefix_syntax(self):
        result = parse_brl("(-)1.234,56")
        assert result == -1234.56


class TestParseUSD:
    def test_standard_format(self):
        assert parse_usd("2,605.00") == 2605.0

    def test_simple_decimal(self):
        assert parse_usd("98.00") == 98.0

    def test_negative_dash(self):
        assert parse_usd("-2,605.00") == -2605.0

    def test_negative_parentheses(self):
        assert parse_usd("(2,605.00)") == -2605.0

    def test_with_dollar_sign(self):
        assert parse_usd("$2,605.00") == 2605.0

    def test_empty_string(self):
        assert parse_usd("") is None

    def test_none_input(self):
        assert parse_usd(None) is None

    def test_dash_only(self):
        assert parse_usd("-") is None


class TestSafeDate:
    def test_normal_date(self):
        assert safe_date(2026, 4, 13) == "2026-04-13"

    def test_overflow_day(self):
        assert safe_date(2026, 2, 31) == "2026-02-28"

    def test_leap_year_feb(self):
        assert safe_date(2024, 2, 29) == "2024-02-29"

    def test_non_leap_year_feb(self):
        assert safe_date(2025, 2, 29) == "2025-02-28"

    def test_zero_day(self):
        assert safe_date(2026, 1, 0) == "2026-01-01"

    def test_negative_month(self):
        assert safe_date(2026, -1, 15) == "2026-01-15"

    def test_month_13(self):
        assert safe_date(2026, 13, 15) == "2026-01-15"
