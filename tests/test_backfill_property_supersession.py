"""Tests — ``dev/backfill_property_supersession.py`` (ADR-324)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PropertyIdentity, User, Workspace
from dev.backfill_property_supersession import _process, _synthetic_entries


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    path = tmp_path / "test_backfill_supersession.db"
    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)
    engine.dispose()
    monkeypatch.setenv("MATHOMS_DATABASE_URL_SYNC", f"sqlite:///{path}")
    return path


def _session_factory(db_file):
    return sessionmaker(bind=create_engine(f"sqlite:///{db_file}", future=True), future=True)


def _add_pair(s, ws_id: str) -> tuple[str, str]:
    specific, generic = str(uuid.uuid4()), str(uuid.uuid4())
    for pid, codigo in ((specific, "12"), (generic, "01")):
        s.add(
            PropertyIdentity(
                id=pid,
                workspace_id=ws_id,
                titular_key="titular",
                codigo_rfb=codigo,
                endereco_canonical="rua exemplo 100",
                first_seen_year=2023,
                descricao_sample="CASA EXEMPLO",
                created_at=datetime.now(timezone.utc),
            )
        )
    return specific, generic


def _seed(db_file) -> tuple[str, str, str]:
    """Workspace com par cross-código (ADR-246): '12' específico vence '01' genérico."""
    factory = _session_factory(db_file)
    with factory() as s:
        user = User(
            id=str(uuid.uuid4()),
            email=f"u-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="x",
            full_name="Test",
        )
        s.add(user)
        s.flush()
        ws = Workspace(id=str(uuid.uuid4()), name="Test WS", owner_id=user.id)
        s.add(ws)
        s.flush()
        specific, generic = _add_pair(s, ws.id)
        s.commit()
        return ws.id, specific, generic


def test_dry_run_plans_without_writing(db_file):
    ws_id, specific, generic = _seed(db_file)
    report = _process(ws_id, dry_run=True)
    assert report["dry_run"] is True
    assert report["baseline_found"] is False
    assert report["to_supersede"] == [generic]
    factory = _session_factory(db_file)
    with factory() as s:
        rows = s.execute(select(PropertyIdentity)).scalars().all()
        assert all(r.superseded_at is None for r in rows)


def test_apply_is_idempotent(db_file):
    ws_id, specific, generic = _seed(db_file)
    first = _process(ws_id, dry_run=False)
    assert first["applied"]["superseded"] == 1
    second = _process(ws_id, dry_run=False)
    assert second["applied"]["superseded"] == 0
    assert second["to_supersede"] == []
    factory = _session_factory(db_file)
    with factory() as s:
        row = s.execute(select(PropertyIdentity).where(PropertyIdentity.id == generic)).scalar_one()
        assert row.superseded_at is not None
        assert row.superseded_by_id == specific


def test_synthetic_entries_map_baseline_values():
    class _Ident:
        def __init__(self, pid):
            self.id = pid
            self.codigo_rfb = "12"
            self.endereco_canonical = "rua exemplo 100"
            self.descricao_sample = "CASA"

    baseline = {"imoveis_consolidados": [{"property_id": "a", "valores_31_12": {"2024": 500000.0}}]}
    entries = _synthetic_entries([_Ident("a"), _Ident("b")], baseline)
    assert entries[0]["valores_31_12"] == {"2024": 500000.0}
    assert entries[1]["valores_31_12"] == {}
