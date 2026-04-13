#!/usr/bin/env python3
"""Tests for E5 age calculation fix."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e5_analyze import calculate_edad


class TestCalculateEdad:
    def test_exact_birthday(self):
        dob = date(1990, 4, 13)
        ref = date(2026, 4, 13)
        assert calculate_edad(dob, ref) == 36

    def test_day_before_birthday(self):
        dob = date(1990, 4, 14)
        ref = date(2026, 4, 13)
        assert calculate_edad(dob, ref) == 35

    def test_day_after_birthday(self):
        dob = date(1990, 4, 12)
        ref = date(2026, 4, 13)
        assert calculate_edad(dob, ref) == 36

    def test_leap_year_birthday(self):
        dob = date(1992, 2, 29)
        ref = date(2026, 2, 28)
        assert calculate_edad(dob, ref) == 33

    def test_leap_year_birthday_on_march1(self):
        dob = date(1992, 2, 29)
        ref = date(2026, 3, 1)
        assert calculate_edad(dob, ref) == 34

    def test_same_date(self):
        dob = date(2000, 1, 1)
        ref = date(2000, 1, 1)
        assert calculate_edad(dob, ref) == 0
