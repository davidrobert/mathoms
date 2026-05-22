"""A18 L3 P1 (ADR-239 D5) — FipeLookupClient Protocol + InMemoryFipeLookup + adapter parser."""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.services.fipe_lookup import (
    BrasilAPIFipeClient,
    FipeLookupError,
    FipeQuote,
    InMemoryFipeLookup,
    _parse_brasilapi_response,
    _parse_brl_currency,
    _ref_month_from_iso,
    _validate_fipe_code,
)

# ─────────────────────── InMemoryFipeLookup ──────────────────────────────


def test_in_memory_returns_quote_when_registered():
    fake = InMemoryFipeLookup()
    fake.register("827125-9", 2024, Decimal("18500.00"), reference_month="2026-05")
    result = fake.fetch("827125-9", 2024)
    assert isinstance(result, FipeQuote)
    assert result.value_brl == Decimal("18500.00")
    assert result.reference_month == "2026-05"
    assert result.source == "in_memory"


def test_in_memory_returns_missing_when_unknown():
    fake = InMemoryFipeLookup()
    result = fake.fetch("999999-X", 2024)
    assert isinstance(result, FipeLookupError)
    assert result.status == "missing"


def test_in_memory_force_pending_refresh():
    """Permite testar caminho de erro sem mock HTTP — útil para testes Celery."""
    fake = InMemoryFipeLookup()
    fake.register("827125-9", 2024, Decimal("18500.00"))
    fake.force_next_status("pending_refresh")
    result = fake.fetch("827125-9", 2024)
    assert isinstance(result, FipeLookupError)
    assert result.status == "pending_refresh"
    # Próxima chamada volta ao normal.
    result2 = fake.fetch("827125-9", 2024)
    assert isinstance(result2, FipeQuote)


def test_in_memory_register_default_reference_month_eh_corrente():
    from datetime import date

    fake = InMemoryFipeLookup()
    fake.register("XYZ-1", 2020, Decimal("10000.00"))
    quote = fake.fetch("XYZ-1", 2020)
    assert isinstance(quote, FipeQuote)
    today = date.today()
    assert quote.reference_month == f"{today.year:04d}-{today.month:02d}"


# ─────────────────────── Validation ───────────────────────────────────────


@pytest.mark.parametrize(
    "code,valid",
    [
        ("827125-9", True),
        ("8271020", True),
        ("15253", True),
        ("ABC", False),  # letras
        ("123", False),  # < 4 chars
        ("", False),
        ("a" * 25, False),  # > 20 chars
    ],
)
def test_validate_fipe_code(code, valid):
    if valid:
        assert _validate_fipe_code(code) is None
    else:
        assert _validate_fipe_code(code) is not None


def test_brasilapi_client_rejeita_code_invalido():
    client = BrasilAPIFipeClient()
    result = client.fetch("ABC", 2024)
    assert isinstance(result, FipeLookupError)
    assert result.status == "missing"
    assert "inválido" in result.reason


# ─────────────────────── Parser BrasilAPI ────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("R$ 18.500,00", Decimal("18500.00")),
        ("R$ 1.234.567,89", Decimal("1234567.89")),
        ("17500.00", Decimal("17500.00")),
        ("", None),
        ("texto invalido", None),
    ],
)
def test_parse_brl_currency(raw, expected):
    assert _parse_brl_currency(raw) == expected


@pytest.mark.parametrize(
    "iso,expected",
    [
        ("2026-05", "2026-05"),
        ("dezembro/2025", "2025-12"),
        ("março/2026", "2026-03"),
        ("", None),  # fallback corrente — verificamos via prefixo
    ],
)
def test_ref_month_from_iso(iso, expected):
    out = _ref_month_from_iso(iso)
    if expected is not None:
        assert out == expected
    else:
        # Fallback ao mês corrente — só valida formato.
        import re as _re

        assert _re.match(r"^\d{4}-\d{2}$", out)


def test_parse_brasilapi_response_seleciona_por_ano_modelo():
    data = [
        {"anoModelo": 2024, "valor": "R$ 18.500,00", "mesReferencia": "maio/2026"},
        {"anoModelo": 2023, "valor": "R$ 17.000,00", "mesReferencia": "maio/2026"},
    ]
    quote = _parse_brasilapi_response("827125-9", 2024, data)
    assert isinstance(quote, FipeQuote)
    assert quote.value_brl == Decimal("18500.00")
    assert quote.reference_month == "2026-05"


def test_parse_brasilapi_response_fallback_primeiro_quando_ano_nao_bate():
    data = [
        {"anoModelo": 2023, "valor": "R$ 17.000,00", "mesReferencia": "maio/2026"},
        {"anoModelo": 2022, "valor": "R$ 16.000,00", "mesReferencia": "maio/2026"},
    ]
    quote = _parse_brasilapi_response("827125-9", 2024, data)
    assert isinstance(quote, FipeQuote)
    assert quote.value_brl == Decimal("17000.00")  # primeiro item


def test_parse_brasilapi_response_empty_returns_missing():
    result = _parse_brasilapi_response("X", 2024, [])
    assert isinstance(result, FipeLookupError)
    assert result.status == "missing"


def test_parse_brasilapi_response_invalid_shape_returns_missing():
    result = _parse_brasilapi_response("X", 2024, "not_a_list")
    assert isinstance(result, FipeLookupError)
    assert result.status == "missing"
