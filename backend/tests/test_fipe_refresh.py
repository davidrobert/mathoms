"""A18 L3 P1 (ADR-239 D5) — Celery task refresh_fipe_value (cache + lookup + persist)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.core.database import Base
from backend.app.models import MarketRate  # noqa: F401 — registra schema
from backend.app.services.fipe_lookup import InMemoryFipeLookup
from backend.app.tasks.fipe_refresh import (
    _CACHE_TTL_DAYS,
    _cache_lookup,
    _fipe_pair,
    _retry_countdown,
    refresh_fipe_value_sync,
)


@pytest.fixture
def sync_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()


# ─────────────────────── Cache hit flow ───────────────────────────────────


def test_cache_hit_returna_quote_sem_chamar_client(sync_db: Session):
    """Cache HIT: row recente em MarketRate → skip client.fetch."""
    today = date.today()
    sync_db.add(
        MarketRate(
            pair=_fipe_pair("827125-9"),
            rate=Decimal("18500.00"),
            observed_at=today - timedelta(days=10),
            reference_month="2026-05",
            source="brasilapi",
        )
    )
    sync_db.flush()

    client = InMemoryFipeLookup()  # NÃO registra nada; se chamado, retornaria missing
    out = refresh_fipe_value_sync("827125-9", 2024, client=client, db=sync_db)
    assert out["status"] == "fresh"
    assert out["source"] == "cache"
    # SQLite Numeric(20, 10) preserva precisão extra; comparar Decimal-to-Decimal.
    assert Decimal(out["value_brl"]) == Decimal("18500.00")


def test_cache_miss_quando_ttl_expirado(sync_db: Session):
    """Cache MISS: row velha (>30 dias) → re-fetch via client."""
    today = date.today()
    sync_db.add(
        MarketRate(
            pair=_fipe_pair("827125-9"),
            rate=Decimal("18500.00"),
            observed_at=today - timedelta(days=_CACHE_TTL_DAYS + 5),
            reference_month="2025-12",
            source="brasilapi",
        )
    )
    sync_db.flush()
    client = InMemoryFipeLookup()
    client.register("827125-9", 2024, Decimal("19000.00"), reference_month="2026-05")
    out = refresh_fipe_value_sync("827125-9", 2024, client=client, db=sync_db)
    assert out["status"] == "fresh"
    assert out["source"] == "in_memory"
    assert out["value_brl"] == "19000.00"


def test_cache_lookup_retorna_none_sem_rows(sync_db: Session):
    assert _cache_lookup(sync_db, "999-X", date.today()) is None


# ─────────────────────── Cache miss + persist ────────────────────────────


def test_miss_persiste_quote_em_market_rates(sync_db: Session):
    client = InMemoryFipeLookup()
    client.register("8271020", 2018, Decimal("11200.00"), reference_month="2026-05")
    out = refresh_fipe_value_sync("8271020", 2018, client=client, db=sync_db)
    assert out["status"] == "fresh"
    rows = sync_db.query(MarketRate).filter_by(pair="fipe_8271020").all()
    assert len(rows) == 1
    assert rows[0].rate == Decimal("11200.00")
    assert rows[0].reference_month == "2026-05"
    assert rows[0].source == "in_memory"


def test_miss_quando_codigo_desconhecido_retorna_missing(sync_db: Session):
    client = InMemoryFipeLookup()  # vazio
    out = refresh_fipe_value_sync("999999-X", 2024, client=client, db=sync_db)
    assert out["status"] == "missing"
    assert out["source"] == "error"
    # Não persiste em MarketRate quando falha.
    assert sync_db.query(MarketRate).count() == 0


def test_pending_refresh_quando_client_force(sync_db: Session):
    """Erro HTTP transitório (429/5xx) → status pending_refresh (sem persist)."""
    client = InMemoryFipeLookup()
    client.register("827125-9", 2024, Decimal("18500.00"))
    client.force_next_status("pending_refresh")
    out = refresh_fipe_value_sync("827125-9", 2024, client=client, db=sync_db)
    assert out["status"] == "pending_refresh"
    assert out["source"] == "error"
    assert sync_db.query(MarketRate).count() == 0


# ─────────────────────── Backoff exponencial ─────────────────────────────


@pytest.mark.parametrize(
    "retries,expected",
    [
        (0, 120),
        (1, 240),
        (2, 480),
        (3, 960),
        (10, 960),  # cap em 2^3
    ],
)
def test_retry_countdown_backoff_exponencial(retries, expected):
    assert _retry_countdown(retries) == expected


# ─────────────────────── Pair canônico ───────────────────────────────────


def test_fipe_pair_prefix():
    assert _fipe_pair("827125-9") == "fipe_827125-9"
    assert _fipe_pair("15253") == "fipe_15253"
