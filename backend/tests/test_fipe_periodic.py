"""A18 L3 P2 (ADR-239 D5) — batch refresh annual + read_fipe_cache."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.core.database import Base
from backend.app.models import MarketRate, User, Vehicle, Workspace  # noqa: F401
from backend.app.tasks.fipe_refresh import (
    _CACHE_TTL_DAYS,
    _enumerate_active_fipe_codes,
    _fipe_pair,
    read_fipe_cache,
    refresh_all_fipe_values_sync,
)


@pytest.fixture
def sync_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def workspace_id(sync_db: Session) -> str:
    from backend.app.core.security import hash_password

    u = User(email="f@test.com", hashed_password=hash_password("p"), full_name="F")
    sync_db.add(u)
    sync_db.flush()
    ws = Workspace(name="WS-F", owner_id=u.id)
    sync_db.add(ws)
    sync_db.flush()
    return ws.id


_VEHICLE_DEFAULTS = dict(
    placa="ABC1D23",
    renavam="12345678900",
    marca="X",
    modelo="Y",
    ano_modelo=2024,
    ano_fabricacao=2024,
    fipe_code="827125-9",
)


def _add_vehicle(db: Session, ws_id: str, **kw) -> Vehicle:
    """Insere vehicle com defaults; `archived=True` marca archived_at; `ano=N` set ambos anos."""
    from datetime import datetime, timezone

    archived = kw.pop("archived", False)
    ano = kw.pop("ano", None)
    if ano is not None:
        kw["ano_modelo"] = kw["ano_fabricacao"] = ano
    v = Vehicle(workspace_id=ws_id, **{**_VEHICLE_DEFAULTS, **kw})
    if archived:
        v.archived_at = datetime.now(timezone.utc)
    db.add(v)
    db.flush()
    return v


# ─────────────────────── Enumerate active vehicles ────────────────────────


def test_enumerate_lista_fipe_codes_distintos(sync_db: Session, workspace_id: str):
    _add_vehicle(sync_db, workspace_id, placa="ABC1D23", renavam="11111111111")
    _add_vehicle(
        sync_db, workspace_id, placa="XYZ9A87", renavam="22222222222", fipe_code="8271020", ano=2018
    )
    _add_vehicle(sync_db, workspace_id, placa="QWE5R67", renavam="33333333333")  # dup (code+ano)
    codes = _enumerate_active_fipe_codes(sync_db)
    assert set(codes) == {("827125-9", 2024), ("8271020", 2018)}


def test_enumerate_ignora_archived(sync_db: Session, workspace_id: str):
    _add_vehicle(sync_db, workspace_id, renavam="11111111111", archived=True)
    assert _enumerate_active_fipe_codes(sync_db) == []


def test_enumerate_ignora_vehicles_sem_fipe_code(sync_db: Session, workspace_id: str):
    _add_vehicle(sync_db, workspace_id, renavam="11111111111", fipe_code=None)
    assert _enumerate_active_fipe_codes(sync_db) == []


# ─────────────────────── refresh_all_fipe_values_sync ────────────────────


def test_refresh_all_enfileira_um_por_distinct(sync_db: Session, workspace_id: str):
    _add_vehicle(sync_db, workspace_id, placa="ABC1D23", renavam="11111111111")
    _add_vehicle(
        sync_db, workspace_id, placa="XYZ9A87", renavam="22222222222", fipe_code="8271020", ano=2018
    )
    enqueued: list[tuple[str, int]] = []
    result = refresh_all_fipe_values_sync(
        db=sync_db, enqueue_fn=lambda c, a: enqueued.append((c, a))
    )
    assert result["enqueued"] == 2
    assert set(enqueued) == {("827125-9", 2024), ("8271020", 2018)}


def test_refresh_all_workspace_sem_vehicles(sync_db: Session):
    enqueued: list = []
    result = refresh_all_fipe_values_sync(
        db=sync_db, enqueue_fn=lambda c, a: enqueued.append((c, a))
    )
    assert result["enqueued"] == 0
    assert enqueued == []


# ─────────────────────── read_fipe_cache ──────────────────────────────────


def test_read_fipe_cache_fresh_quando_row_recente(sync_db: Session):
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
    value, status = read_fipe_cache(sync_db, "827125-9", today=today)
    assert value == Decimal("18500.00")
    assert status == "fresh"


def test_read_fipe_cache_stale_acceptable_quando_row_velha(sync_db: Session):
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
    value, status = read_fipe_cache(sync_db, "827125-9", today=today)
    assert value == Decimal("18500.00")
    assert status == "stale_acceptable"


def test_read_fipe_cache_pending_refresh_sem_row(sync_db: Session):
    value, status = read_fipe_cache(sync_db, "999-X")
    assert value is None
    assert status == "pending_refresh"


# ─────────────────────── Beat schedule sanity ────────────────────────────


def test_beat_schedule_fipe_refresh_annual_registrado():
    from backend.app.worker import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "fipe-refresh-annual" in schedule
    assert schedule["fipe-refresh-annual"]["task"] == "fin.fipe.refresh_all_annual"
