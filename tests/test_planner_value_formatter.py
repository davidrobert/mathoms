"""Unit tests do formatter compartilhado (ADR-203 §D8)."""

from __future__ import annotations

import pytest

from pipeline.llm.value_formatter import format_value


class TestFormatValueRaw:
    def test_raw_passes_through_value(self):
        assert format_value(42, "raw") == 42
        assert format_value("hello", "raw") == "hello"
        assert format_value(None, "raw") is None


class TestFormatValueBRL:
    def test_brl_with_int(self):
        assert format_value(1234, "brl") == "R$ 1.234,00"

    def test_brl_with_float(self):
        assert format_value(1234.56, "brl") == "R$ 1.234,56"

    def test_brl_negative(self):
        assert format_value(-1234.56, "brl") == "-R$ 1.234,56"

    def test_brl_string_numeric(self):
        # str numérica com vírgula brasileira
        assert format_value("1234,56", "brl") == "R$ 1.234,56"

    def test_brl_none(self):
        assert format_value(None, "brl") == "—"

    def test_brl_non_numeric_string(self):
        # str não numérica — retorna str original (não quebra LLM)
        assert format_value("N/D", "brl") == "N/D"

    def test_brl_large_value(self):
        assert format_value(1_000_000, "brl") == "R$ 1.000.000,00"

    def test_brl_half_cent_rounds_half_up_decimal(self):
        # ADR-090/296: cents via Decimal(str(v)) + ROUND_HALF_UP. float round()
        # daria "R$ 2,67" (float(2.675)=2.67499…); Decimal trava em "R$ 2,68",
        # byte-idêntico ao _to_cents do verificador (parecer_evidencia).
        assert format_value(2.675, "brl") == "R$ 2,68"


class TestFormatValuePct:
    def test_pct_absolute_value_adr209(self):
        # ADR-209: 44.7 → "44,7%" (absoluto, NUNCA "4470%" nem "0,447%")
        assert format_value(44.7, "pct") == "44,7%"

    def test_pct_low_value_valid(self):
        # ADR-209 caso limítrofe: 0.5 → "0,5%" (não "50%")
        assert format_value(0.5, "pct") == "0,5%"

    def test_pct_over_100_valid(self):
        # ADR-209: cobertura_despesa_essencial_pct=350.0 → "350,0%"
        assert format_value(350.0, "pct") == "350,0%"

    def test_pct_negative(self):
        assert format_value(-12.3, "pct") == "-12,3%"

    def test_percent2_two_decimals(self):
        assert format_value(44.7, "percent2") == "44,70%"

    def test_pct_string_legacy(self):
        # legado: "3.20" (4 campos ratios em string)
        assert format_value("3.20", "pct") == "3,2%"

    def test_pct_none(self):
        assert format_value(None, "pct") == "—"


class TestFormatValueInt:
    def test_int_basic(self):
        assert format_value(1234, "int") == "1234"

    def test_int_float_rounds(self):
        assert format_value(1234.7, "int") == "1235"

    def test_int_none(self):
        assert format_value(None, "int") == "—"


class TestFormatValueString:
    def test_string_basic(self):
        assert format_value(42, "string") == "42"
        assert format_value("hello", "string") == "hello"
        assert format_value(None, "string") == "—"


class TestFormatValueValidation:
    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="unknown format hint"):
            format_value(42, "invalid_fmt")  # type: ignore[arg-type]
