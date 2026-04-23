#!/usr/bin/env python3
"""Tests for E2 bank parser registry and parsing functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e2.common import (
    _valid_ym,
    infer_periodo_from_filename,
    parse_brl,
    parse_usd,
    safe_date,
)
from scripts.e2.registry import is_non_statement_type, is_processable, route_to_parser

# =============================================================================
# Registry routing tests
# =============================================================================


class TestParserRegistry:
    """Verify that known filenames route to the correct parser."""

    def test_c6bank_extrato_csv(self):
        assert route_to_parser("c6bank_extratoconta_202601_202601-0_original.csv") is not None

    def test_c6bank_pj_csv(self):
        assert route_to_parser("c6bank_extratocontapj_202601_202601-0_original.csv") is not None

    def test_c6bank_global_usd(self):
        assert (
            route_to_parser("c6bank_extratocontaglobalusd_202601_202601-0_original.pdf") is not None
        )

    def test_c6bank_carbon_csv(self):
        assert route_to_parser("c6bank_faturacarbon_202603-0_original.csv") is not None

    def test_c6bank_carbon_pdf(self):
        assert route_to_parser("c6bank_faturacarbon_202603-0_original.pdf") is not None

    def test_itau_xls(self):
        assert route_to_parser("itau_extratoconta_202601_202604-0_original.xls") is not None

    def test_itau_personnalite_xls(self):
        assert (
            route_to_parser("itau_extratocontapersonnalite_202601_202604-0_original.xls")
            is not None
        )

    def test_itau_paoacucar_csv(self):
        assert route_to_parser("itau_faturapaoacucar_202603-0_original.csv") is not None

    def test_santander_xls(self):
        assert route_to_parser("santander_extratoconta_202601_202604-0_original.xls") is not None

    def test_santander_unique_csv(self):
        assert route_to_parser("santander_faturaunique_202603-0_original.csv") is not None

    def test_santander_cdb_xlsx(self):
        assert route_to_parser("santander_cdbresumo_202604-0_original.xlsx") is not None

    def test_bradesco_xls(self):
        # Bradesco extrato routing
        parser = route_to_parser("bradesco_extratoconta_202601_202604-0_original.xls")
        assert parser is not None

    def test_wise_pdf(self):
        assert (
            route_to_parser("wise_extratocontaglobalusd_202601_202604-0_original.pdf") is not None
        )

    def test_picpay_pdf(self):
        assert route_to_parser("picpay_extratoconta_202601_202604-0_original.pdf") is not None

    def test_unknown_file_returns_none(self):
        assert route_to_parser("random_document.txt") is None

    def test_unknown_bank_returns_none(self):
        assert route_to_parser("nubank_extratoconta_202601-0_original.csv") is None

    def test_itau_extrato_with_hash_prefix(self):
        # ADR-084: canonical filenames receive a {sha256[:12]}_ prefix. Parsers
        # were written pre-ADR; registry normalizes `^` so prefix is optional.
        assert route_to_parser("79340de51709_itau_extratoconta_2026-0_original.xls") is not None

    def test_bradesco_extrato_with_hash_prefix(self):
        assert route_to_parser("abcdef012345_bradesco_extratoconta_2026-0_original.pdf") is not None

    def test_santander_extrato_with_hash_prefix(self):
        assert (
            route_to_parser("deadbeef1234_santander_extratoconta_202601-0_original.xls") is not None
        )


class TestItauCdbBinaryXls:
    """Itaú cdbdetalhes export is sometimes binary .xls (CDFV2) instead of
    HTML-as-xls — parser must not crash with UnicodeDecodeError."""

    def test_binary_xls_falls_back_to_llm(self, tmp_path):
        from scripts.e2.banks.itau import parse_itau_cdb_html_xls

        # CDFV2 magic header (Microsoft Compound File)
        p = tmp_path / "itau_cdbdetalhes_2026.xls"
        p.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 200)
        result = parse_itau_cdb_html_xls(p, p.name)
        assert result.get("requires_llm_fallback") is True
        assert any("XLS binário" in n for n in result["notas"])


class TestIsProcessable:
    def test_known_file(self):
        assert is_processable("c6bank_extratoconta_202601_202601-0_original.csv") is True

    def test_unknown_file(self):
        assert is_processable("random.txt") is False


class TestIsNonStatementType:
    def test_investimento(self):
        assert is_non_statement_type("c6bank_investimentosposicao_202604-0_original.pdf") is True

    def test_irpf(self):
        assert is_non_statement_type("receitafederal_irpfdeclaracao_2025-0_original.pdf") is True

    def test_extrato(self):
        assert is_non_statement_type("c6bank_extratoconta_202601-0_original.csv") is False


# =============================================================================
# Period validation tests (P5)
# =============================================================================


class TestValidYM:
    def test_valid(self):
        assert _valid_ym(2026, 1) is True
        assert _valid_ym(2018, 12) is True

    def test_invalid_month(self):
        assert _valid_ym(2026, 0) is False
        assert _valid_ym(2026, 13) is False

    def test_invalid_year(self):
        assert _valid_ym(2017, 6) is False
        assert _valid_ym(2031, 6) is False


class TestInferPeriodoValidation:
    def test_valid_range(self):
        inicio, fim = infer_periodo_from_filename("itau_extratoconta_202601_202604-0_original.xls")
        assert inicio == "2026-01-01"
        assert fim == "2026-04-30"

    def test_valid_single(self):
        inicio, fim = infer_periodo_from_filename("c6bank_faturacarbon_202603-0_original.csv")
        assert inicio == "2026-03-01"
        assert fim == "2026-03-31"

    def test_invalid_month_returns_none(self, capsys):
        inicio, fim = infer_periodo_from_filename("test_202613-0_original.csv")
        assert inicio is None
        assert fim is None

    def test_invalid_year_returns_none(self, capsys):
        inicio, fim = infer_periodo_from_filename("test_201501_201512-0_original.csv")
        assert inicio is None
        assert fim is None


# =============================================================================
# Edge cases in value parsing
# =============================================================================


class TestParseBRLEdgeCases:
    def test_very_large_number(self):
        assert parse_brl("99.999.999,99") == 99999999.99

    def test_single_digit(self):
        assert parse_brl("5") == 5.0

    def test_negative_zero(self):
        result = parse_brl("-0,00")
        assert result is not None
        assert abs(result) < 0.01

    def test_double_spaces(self):
        assert parse_brl("  R$  1.234,56  ") == 1234.56


class TestParseUSDEdgeCases:
    def test_no_cents(self):
        assert parse_usd("1,000") == 1000.0

    def test_single_dollar(self):
        assert parse_usd("$1.50") == 1.50

    def test_negative_with_parens(self):
        assert parse_usd("($500.00)") == -500.0


class TestSafeDateEdgeCases:
    def test_month_overflow_clamps(self):
        # Month > 12 should clamp to valid
        result = safe_date(2026, 13, 15)
        assert result is not None

    def test_day_zero_clamps(self):
        result = safe_date(2026, 1, 0)
        assert result == "2026-01-01"

    def test_february_leap_year(self):
        assert safe_date(2028, 2, 29) == "2028-02-29"

    def test_february_non_leap(self):
        assert safe_date(2026, 2, 29) == "2026-02-28"
