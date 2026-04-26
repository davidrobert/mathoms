"""Tests do ConfigStore Protocol + FileConfigStore + InMemoryConfigStore (A7.0 · ADR-134)."""

from __future__ import annotations

import sys
import warnings
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.adapters import FileConfigStore, InMemoryConfigStore  # noqa: E402
from pipeline.domain.types.config import (  # noqa: E402
    CategorizationConfig,
    CategoryDef,
    FamilyMemberRecord,
    FamilyMembersConfig,
    FiscalParameters,
    InstitutionDef,
    InstitutionsCatalog,
    ReportLayout,
    TransferConfig,
    TransferInternalConfig,
)
from pipeline.ports import ConfigStore  # noqa: E402

# ---------------------------------------------------------------------------
# Protocol shape
# ---------------------------------------------------------------------------


def test_file_config_store_satisfies_protocol():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        store = FileConfigStore()
    assert isinstance(store, ConfigStore)


def test_in_memory_config_store_satisfies_protocol():
    store = InMemoryConfigStore()
    assert isinstance(store, ConfigStore)


# ---------------------------------------------------------------------------
# FileConfigStore — DeprecationWarning + tipos
# ---------------------------------------------------------------------------


def test_file_config_store_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as recs:
        warnings.simplefilter("always")
        FileConfigStore()
    assert any(issubclass(r.category, DeprecationWarning) for r in recs)


def test_file_config_store_categorization_returns_typed_config():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        store = FileConfigStore()
    cat = store.get_categorization("any-workspace")
    assert isinstance(cat, CategorizationConfig)
    assert all(isinstance(c, CategoryDef) for c in cat.categories.values())


def test_file_config_store_family_members_parses_real_file():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        store = FileConfigStore()
    fm = store.get_family_members("any-workspace")
    if fm is None:
        pytest.skip("config/family_members.json not available")
    assert isinstance(fm, FamilyMembersConfig)
    assert all(isinstance(m, FamilyMemberRecord) for m in fm.members)


def test_file_config_store_institutions_returns_catalog():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        store = FileConfigStore()
    inst = store.get_institutions()
    assert isinstance(inst, InstitutionsCatalog)
    assert all(isinstance(i, InstitutionDef) for i in inst.institutions.values())


def test_file_config_store_report_layout_returns_or_none():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        store = FileConfigStore()
    rl = store.get_report_layout("any-workspace")
    assert rl is None or isinstance(rl, ReportLayout)


def test_file_config_store_transfer_config_returns_or_none():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        store = FileConfigStore()
    tc = store.get_transfer_config("any-workspace")
    assert tc is None or isinstance(tc, TransferConfig)


def test_file_config_store_fiscal_raises_not_implemented():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        store = FileConfigStore()
    with pytest.raises(NotImplementedError, match="A7.2b"):
        store.get_fiscal_for_period(date(2025, 1, 1), date(2025, 12, 31))


def test_file_config_store_market_rate_raises_not_implemented():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        store = FileConfigStore()
    with pytest.raises(NotImplementedError, match="A7.2b"):
        store.get_market_rate("USD/BRL", date(2026, 4, 26))


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
