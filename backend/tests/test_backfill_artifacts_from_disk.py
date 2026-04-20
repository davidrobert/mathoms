"""Tests — ``backend.app.scripts.backfill_artifacts_from_disk`` (Fase 4.6)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import (
    PipelineArtifact,
    PipelineRun,
    PipelineRunStatus,
    User,
    Workspace,
)


def _seed_disk(storage_root: Path, workspace_id: str) -> None:
    processed = storage_root / workspace_id / "processed"
    (processed / "E3_reconciled").mkdir(parents=True)
    (processed / "E3_reconciled" / "itau_BRL-3_reconciled.json").write_text(
        json.dumps({"net": 100})
    )
    (processed / "E4_unified").mkdir(parents=True)
    (processed / "E4_unified" / "despesas-4_unified.json").write_text(
        json.dumps({"total": 500})
    )
    (processed / "E5_analysis").mkdir(parents=True)
    (processed / "E5_analysis" / "analise_financeira-5_analysis.json").write_text(
        json.dumps({"score": 80})
    )


@pytest.fixture
def sync_db(tmp_path):
    """Sync engine em arquivo isolado — backfill usa sync session."""
    db_file = tmp_path / "test_backfill.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


def _seed_workspace_sync(factory, *, email: str = "bf@test.com"):
    with factory() as s:
        user = User(email=email, hashed_password=hash_password("p"), full_name="B")
        s.add(user)
        s.flush()
        ws = Workspace(name="WS", owner_id=user.id)
        s.add(ws)
        s.flush()
        run = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.completed)
        s.add(run)
        s.commit()
        return ws.id


def test_backfill_dry_run_creates_nothing(sync_db, tmp_path, monkeypatch):
    from backend.app.core import config as config_module
    from backend.app.scripts import backfill_artifacts_from_disk as bf

    ws_id = _seed_workspace_sync(sync_db, email="bfdry@test.com")
    monkeypatch.setattr(config_module.settings, "STORAGE_ROOT", tmp_path)
    bf.set_session_factory(sync_db)
    _seed_disk(tmp_path, ws_id)

    rc = bf.main(["--dry-run", "--workspace-id", ws_id])
    assert rc == 0

    with sync_db() as s:
        rows = s.execute(select(PipelineArtifact)).scalars().all()
        assert rows == []


def test_backfill_apply_creates_artifacts(sync_db, tmp_path, monkeypatch):
    from backend.app.core import config as config_module
    from backend.app.scripts import backfill_artifacts_from_disk as bf

    ws_id = _seed_workspace_sync(sync_db, email="bfapply@test.com")
    monkeypatch.setattr(config_module.settings, "STORAGE_ROOT", tmp_path)
    bf.set_session_factory(sync_db)
    _seed_disk(tmp_path, ws_id)

    rc = bf.main(["--apply", "--workspace-id", ws_id])
    assert rc == 0

    with sync_db() as s:
        rows = s.execute(select(PipelineArtifact)).scalars().all()
        stages = sorted({r.stage for r in rows})
        assert stages == ["E3", "E4", "E5"]
        e5 = next(r for r in rows if r.stage == "E5")
        assert e5.content_json == {"score": 80}


def test_backfill_is_idempotent(sync_db, tmp_path, monkeypatch):
    from backend.app.core import config as config_module
    from backend.app.scripts import backfill_artifacts_from_disk as bf

    ws_id = _seed_workspace_sync(sync_db, email="bfid@test.com")
    monkeypatch.setattr(config_module.settings, "STORAGE_ROOT", tmp_path)
    bf.set_session_factory(sync_db)
    _seed_disk(tmp_path, ws_id)

    bf.main(["--apply", "--workspace-id", ws_id])
    with sync_db() as s:
        first = len(s.execute(select(PipelineArtifact)).scalars().all())
    bf.main(["--apply", "--workspace-id", ws_id])
    with sync_db() as s:
        second = len(s.execute(select(PipelineArtifact)).scalars().all())
    assert first == second == 3
