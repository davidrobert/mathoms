"""FiscalParameter + MarketRate repos + DBConfigStore extension (A7.2b · ADR-135)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.fiscal_parameter import FiscalParameter
from backend.app.models.market_rate import MarketRate
from backend.app.repositories.fiscal_parameter_repository import (
    FiscalParameterAmbiguous,
    FiscalParameterNotFound,
    FiscalParameterRepository,
)
from backend.app.repositories.market_rate_repository import (
    MarketRateNotFound,
    MarketRateRepository,
)


@pytest.fixture
def sync_db(tmp_path):
    """Sync engine isolado por teste — repos consomem Session sync."""
    db_file = tmp_path / "test_fiscal.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


def _make_fiscal(
    *,
    year: int,
    effective_from: date,
    effective_to: date | None,
    source: str = "test",
    lp: Decimal = Decimal("0.32"),
) -> FiscalParameter:
    return FiscalParameter(
        id=str(uuid.uuid4()),
        year=year,
        ir_brackets=[{"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 0}],
        pgbl_limit_brl_cents=0,
        inss_ceiling_brl_cents=0,
        lucro_presumido_aliquota=lp,
        effective_from=effective_from,
        effective_to=effective_to,
        source=source,
        created_at=datetime.now(timezone.utc),
    )


def _make_rate(*, pair: str, observed_at: date, rate: Decimal, source: str = "test") -> MarketRate:
    return MarketRate(
        id=str(uuid.uuid4()),
        pair=pair,
        rate=rate,
        observed_at=observed_at,
        source=source,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# FiscalParameterRepository
# ---------------------------------------------------------------------------


class TestFiscalParameterRepository:
    def test_get_for_period_returns_single_row(self, sync_db):
        with sync_db() as s:
            s.add(_make_fiscal(year=2025, effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31)))
            s.commit()
            row = FiscalParameterRepository(s).get_for_period(date(2025, 6, 1), date(2025, 6, 30))
            assert row.year == 2025

    def test_get_for_period_open_ended_effective_to(self, sync_db):
        with sync_db() as s:
            s.add(_make_fiscal(year=2026, effective_from=date(2026, 1, 1), effective_to=None))
            s.commit()
            row = FiscalParameterRepository(s).get_for_period(
                date(2030, 1, 1), date(2030, 12, 31)
            )
            assert row.year == 2026

    def test_get_for_period_raises_not_found(self, sync_db):
        with sync_db() as s:
            with pytest.raises(FiscalParameterNotFound):
                FiscalParameterRepository(s).get_for_period(date(2025, 1, 1), date(2025, 12, 31))

    def test_get_for_period_raises_ambiguous_on_overlap(self, sync_db):
        with sync_db() as s:
            s.add(_make_fiscal(year=2025, effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31)))
            s.add(
                _make_fiscal(
                    year=2025,
                    effective_from=date(2025, 7, 1),
                    effective_to=date(2025, 12, 31),
                    source="reform_mid_year",
                )
            )
            s.commit()
            with pytest.raises(FiscalParameterAmbiguous):
                FiscalParameterRepository(s).get_for_period(
                    date(2025, 8, 1), date(2025, 8, 31)
                )

    def test_list_covering_period_returns_only_rows_that_span_full_window(self, sync_db):
        """Vigência exclusiva: para cobrir [start, end], precisa effective_from<=start AND effective_to>=end."""
        with sync_db() as s:
            s.add(_make_fiscal(year=2024, effective_from=date(2024, 1, 1), effective_to=date(2024, 12, 31)))
            s.add(_make_fiscal(year=2025, effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31)))
            s.commit()
            # Ano fiscal único 2025 cobre [2025-06-01, 2025-06-30]; 2024 não cobre.
            rows = FiscalParameterRepository(s).list_covering_period(date(2025, 6, 1), date(2025, 6, 30))
            assert [r.year for r in rows] == [2025]

    def test_list_covering_period_returns_empty_when_window_spans_two_years(self, sync_db):
        """Janela cruzando ano fiscal sem row contínua → empty (motiva ambiguidade)."""
        with sync_db() as s:
            s.add(_make_fiscal(year=2024, effective_from=date(2024, 1, 1), effective_to=date(2024, 12, 31)))
            s.add(_make_fiscal(year=2025, effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31)))
            s.commit()
            rows = FiscalParameterRepository(s).list_covering_period(date(2024, 12, 1), date(2025, 1, 31))
            assert rows == []

    def test_get_by_year_returns_match_or_none(self, sync_db):
        with sync_db() as s:
            s.add(_make_fiscal(year=2025, effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31)))
            s.commit()
            assert FiscalParameterRepository(s).get_by_year(2025).year == 2025
            assert FiscalParameterRepository(s).get_by_year(2099) is None

    def test_list_all(self, sync_db):
        with sync_db() as s:
            for year in (2024, 2025, 2026):
                s.add(_make_fiscal(year=year, effective_from=date(year, 1, 1), effective_to=date(year, 12, 31)))
            s.commit()
            rows = FiscalParameterRepository(s).list_all()
            assert [r.year for r in rows] == [2026, 2025, 2024]


# ---------------------------------------------------------------------------
# MarketRateRepository
# ---------------------------------------------------------------------------


class TestMarketRateRepository:
    def test_get_latest_on_or_before_returns_most_recent(self, sync_db):
        with sync_db() as s:
            s.add(_make_rate(pair="USD/BRL", observed_at=date(2024, 1, 1), rate=Decimal("5.0")))
            s.add(_make_rate(pair="USD/BRL", observed_at=date(2025, 6, 1), rate=Decimal("5.5")))
            s.add(_make_rate(pair="USD/BRL", observed_at=date(2026, 1, 1), rate=Decimal("5.8")))
            s.commit()
            row = MarketRateRepository(s).get_latest_on_or_before("USD/BRL", date(2025, 12, 31))
            assert row.rate == Decimal("5.5000000000")
            assert row.observed_at == date(2025, 6, 1)

    def test_get_latest_on_or_before_returns_none_when_no_history(self, sync_db):
        with sync_db() as s:
            row = MarketRateRepository(s).get_latest_on_or_before("USD/BRL", date(2025, 12, 31))
            assert row is None

    def test_get_latest_on_or_before_excludes_future_rows(self, sync_db):
        with sync_db() as s:
            s.add(_make_rate(pair="USD/BRL", observed_at=date(2027, 1, 1), rate=Decimal("6.0")))
            s.commit()
            row = MarketRateRepository(s).get_latest_on_or_before("USD/BRL", date(2026, 1, 1))
            assert row is None

    def test_get_rate_returns_decimal(self, sync_db):
        with sync_db() as s:
            s.add(_make_rate(pair="EUR/BRL", observed_at=date(2026, 1, 1), rate=Decimal("6.35")))
            s.commit()
            rate = MarketRateRepository(s).get_rate("EUR/BRL", date(2026, 4, 1))
            assert rate == Decimal("6.3500000000")

    def test_get_rate_raises_not_found(self, sync_db):
        with sync_db() as s:
            with pytest.raises(MarketRateNotFound):
                MarketRateRepository(s).get_rate("USD/BRL", date(2025, 1, 1))

    def test_unique_constraint_pair_observed_at(self, sync_db):
        with sync_db() as s:
            s.add(_make_rate(pair="USD/BRL", observed_at=date(2025, 1, 1), rate=Decimal("5.0")))
            s.commit()
            s.add(_make_rate(pair="USD/BRL", observed_at=date(2025, 1, 1), rate=Decimal("5.5")))
            with pytest.raises(Exception):  # IntegrityError shape varies per backend
                s.commit()

    def test_list_by_pair_ordered_recent_first(self, sync_db):
        with sync_db() as s:
            s.add(_make_rate(pair="USD/BRL", observed_at=date(2024, 1, 1), rate=Decimal("5.0")))
            s.add(_make_rate(pair="USD/BRL", observed_at=date(2026, 1, 1), rate=Decimal("5.8")))
            s.add(_make_rate(pair="EUR/BRL", observed_at=date(2026, 1, 1), rate=Decimal("6.4")))
            s.commit()
            rows = MarketRateRepository(s).list_by_pair("USD/BRL")
            assert [r.observed_at for r in rows] == [date(2026, 1, 1), date(2024, 1, 1)]
