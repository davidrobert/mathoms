#!/usr/bin/env python3
"""Tests for E5.N formatting functions and MetricsProxy behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e5n_narrativas import (
    fmt_currency, fmt_percent, fmt_num, fmt_usd, _MetricsProxy,
)


class TestMetricsProxy:
    def test_missing_key_returns_none(self):
        m = _MetricsProxy({"a": 1})
        assert m["missing"] is None

    def test_existing_key_returns_value(self):
        m = _MetricsProxy({"score": 6.8})
        assert m["score"] == 6.8

    def test_zero_is_not_none(self):
        m = _MetricsProxy({"zero": 0})
        assert m["zero"] == 0
        assert m["zero"] is not None


class TestFmtCurrencyNone:
    def test_none_returns_nd(self):
        assert fmt_currency(None) == "N/D"

    def test_zero_returns_formatted(self):
        result = fmt_currency(0)
        assert "0" in result
        assert result != "N/D"

    def test_positive_thousands(self):
        result = fmt_currency(1500)
        assert "1,5k" in result or "1.500" in result

    def test_millions(self):
        result = fmt_currency(2500000)
        assert "M" in result

    def test_negative(self):
        result = fmt_currency(-1500)
        assert "-" in result


class TestFmtPercentNone:
    def test_none_returns_nd(self):
        assert fmt_percent(None) == "N/D"

    def test_integer_percent(self):
        assert fmt_percent(50) == "50%"

    def test_decimal_percent(self):
        result = fmt_percent(18.8)
        assert "18,8%" == result


class TestFmtNumNone:
    def test_none_returns_nd(self):
        assert fmt_num(None) == "N/D"

    def test_integer(self):
        assert fmt_num(42) == "42"

    def test_decimal(self):
        assert fmt_num(3.14159, decimals=2) == "3,14"


class TestFmtUsdNone:
    def test_none_returns_nd(self):
        assert fmt_usd(None) == "N/D"

    def test_thousands(self):
        result = fmt_usd(2500)
        assert "2,5k" in result

    def test_small_value(self):
        result = fmt_usd(500)
        assert "500" in result
