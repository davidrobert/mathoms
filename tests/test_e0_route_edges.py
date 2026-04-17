#!/usr/bin/env python3
"""Edge-case unit tests for E0-route helpers (7D.1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e0_route import _validate_period, build_final_name, extract_period


class TestValidatePeriod:
    def test_valid_month(self):
        assert _validate_period("202604") is True

    def test_invalid_month_13(self):
        assert _validate_period("202613") is False

    def test_wrong_length(self):
        assert _validate_period("20260") is False


class TestExtractPeriod:
    def test_fallback_to_yyyymmdd_when_no_match(self, monkeypatch):
        from datetime import date as real_date

        class _FixedDate:
            @staticmethod
            def today():
                return real_date(2026, 4, 17)

        monkeypatch.setattr("scripts.e0_route.date", _FixedDate)
        assert extract_period("no_period_here.pdf") == "20260417"


class TestBuildFinalName:
    def test_llm_final_name_sanitized(self):
        name = build_final_name(
            {
                "source": "llm",
                "final_name": "../../evil.pdf",
                "dest_group": "members",
                "doc_type": "holerite",
                "period": "202604",
                "member": "titular",
            },
            ".pdf",
        )
        assert ".." not in name
        assert name.endswith(".pdf")

    def test_bank_statement_pattern(self):
        n = build_final_name(
            {
                "source": "regex",
                "dest_group": "banking",
                "institution": "itau",
                "doc_type": "extrato",
                "period": "202604",
            },
            ".pdf",
        )
        assert n.startswith("itau_extrato_202604")
        assert n.endswith("-0_original.pdf")
