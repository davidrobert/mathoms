"""Tests para ``normalize_account_number`` (ADR-226 §1)."""

import pytest

from pipeline.domain.services.account_normalization import normalize_account_number


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("123456", "123456"),
        ("12345-6", "123456"),
        ("12.345-6", "123456"),
        ("12/345 6", "123456"),
        ("abc 123-45 def", "12345"),
        ("---", None),
    ],
)
def test_normalize_variants(raw: str | None, expected: str | None) -> None:
    assert normalize_account_number(raw) == expected
