"""Tests do ConfigStore Protocol + InMemoryConfigStore (A7.0 · ADR-134)."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.adapters import InMemoryConfigStore  # noqa: E402
from pipeline.domain.types.config import (  # noqa: E402
    CategorizationConfig,
    CategoryDef,
    FamilyMemberRecord,
    FamilyMembersConfig,
    FiscalParameters,
    InstitutionsCatalog,
    TransferInternalConfig,
)
from pipeline.ports import ConfigStore  # noqa: E402

# ---------------------------------------------------------------------------
# Protocol shape
# ---------------------------------------------------------------------------


def test_in_memory_config_store_satisfies_protocol():
    store = InMemoryConfigStore()
    assert isinstance(store, ConfigStore)


# ---------------------------------------------------------------------------
# InMemoryConfigStore — round-trip
# ---------------------------------------------------------------------------


def test_in_memory_config_store_returns_injected_categorization():
    cat = CategorizationConfig(
        categories={"alimentacao": CategoryDef("alimentacao", "Alimentação", ("MERCADO",))}
    )
    store = InMemoryConfigStore(categorization=cat)
    assert store.get_categorization("ws-1") is cat


def test_in_memory_config_store_returns_none_when_not_configured():
    store = InMemoryConfigStore()
    assert store.get_categorization("ws-1") is None
    assert store.get_family_members("ws-1") is None
    assert store.get_report_layout("ws-1") is None
    assert store.get_transfer_config("ws-1") is None


def test_in_memory_config_store_returns_empty_catalog_by_default():
    store = InMemoryConfigStore()
    inst = store.get_institutions()
    assert isinstance(inst, InstitutionsCatalog)
    assert inst.institutions == {}


def test_in_memory_config_store_fiscal_lookup_by_year():
    params_2025 = FiscalParameters(year=2025, source="seed-2025")
    store = InMemoryConfigStore(fiscal_by_year={2025: params_2025})
    got = store.get_fiscal_for_period(date(2025, 3, 1), date(2025, 3, 31))
    assert got is params_2025


def test_in_memory_config_store_fiscal_missing_year_raises():
    store = InMemoryConfigStore()
    with pytest.raises(KeyError, match="year=2025"):
        store.get_fiscal_for_period(date(2025, 1, 1), date(2025, 12, 31))


def test_in_memory_config_store_market_rate_returns_decimal():
    rates = {("USD/BRL", date(2026, 4, 26)): Decimal("5.10")}
    store = InMemoryConfigStore(market_rates=rates)
    got = store.get_market_rate("USD/BRL", date(2026, 4, 26))
    assert got == Decimal("5.10")
    assert isinstance(got, Decimal)


def test_in_memory_config_store_market_rate_missing_raises():
    store = InMemoryConfigStore()
    with pytest.raises(KeyError, match="USD/BRL"):
        store.get_market_rate("USD/BRL", date(2026, 4, 26))


def test_in_memory_config_store_with_full_family_config():
    members = (
        FamilyMemberRecord(
            key="alice",
            full_name="Alice da Silva",
            short_name="Alice",
            role="titular",
        ),
    )
    transfers = TransferInternalConfig(recipients=("alice",), patterns_pix=("alice@email",))
    fm = FamilyMembersConfig(
        members=members,
        bank_to_member={"itau": "alice"},
        family_surname="Silva",
        transfers=transfers,
    )
    store = InMemoryConfigStore(family_members=fm)
    out = store.get_family_members("any")
    assert out is fm
    assert out.transfers is transfers
