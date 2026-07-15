#!/usr/bin/env python3
"""Edge-case unit tests for E5 / E5.N helpers (7D.2)."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.analyze_finances import calculate_edad, is_one_time_income
from scripts.generate_narratives import _safe_div, validate_narrativas


class TestE5AnalyzeEdges:
    def test_calculate_edad_birthday_not_yet(self):
        dob = date(1990, 6, 15)
        ref = date(2026, 6, 10)
        assert calculate_edad(dob, ref) == 35

    def test_is_one_time_income_keyword(self):
        assert is_one_time_income("BONUS 13o SALARIO") is True


class TestE5NEdges:
    def test_safe_div_by_zero(self):
        assert _safe_div(10, 0, default=-1) == -1

    def test_validate_narrativas_empty(self):
        ok, errs = validate_narrativas({})
        assert ok is False
        assert len(errs) >= 3
