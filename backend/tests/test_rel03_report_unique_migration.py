"""Migration ``rel03reportuniq`` — índice único parcial em ``reports`` +
detecção de duplicatas pré-existentes (REL-03)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.command import downgrade, upgrade
from alembic.config import Config

pytestmark = pytest.mark.migration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
ALEMBIC_DIR = PROJECT_ROOT / "backend" / "alembic"

PARENT_REVISION = "adr291baserun"
TARGET_REVISION = "rel03reportuniq"
INDEX_NAME = "ux_reports_workspace_pipeline_run"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_at_parent(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="rel03_test_")
    os.close(fd)
    db_path = Path(db_path_str)
    async_url = f"sqlite+aiosqlite:///{db_path}"

    monkeypatch.setenv("MATHOMS_DATABASE_URL", async_url)
    from backend.app.core import config as core_config

    core_config.settings.DATABASE_URL = async_url

    cfg = _alembic_config(async_url)
    upgrade(cfg, PARENT_REVISION)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    yield engine, cfg

    engine.dispose()
    db_path.unlink(missing_ok=True)


def _index_sql(conn, name: str) -> str | None:
    row = conn.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='index' AND name=:n"),
        {"n": name},
    ).fetchone()
    return row[0] if row else None


def _insert_report(conn, rid: str, ws_id: str, run_id: str | None) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO reports (id, workspace_id, pipeline_run_id, title, created_at) "
            "VALUES (:id, :ws, :run, :title, :ts)"
        ),
        {"id": rid, "ws": ws_id, "run": run_id, "title": "t", "ts": "2026-06-18T00:00:00"},
    )


def test_upgrade_creates_partial_unique_index(alembic_at_parent) -> None:
    engine, cfg = alembic_at_parent
    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        sql = _index_sql(conn, INDEX_NAME)
        assert sql is not None
        low = sql.lower()
        assert "unique" in low and "workspace_id" in low and "pipeline_run_id" in low
        assert "pipeline_run_id is not null" in low

    with engine.begin() as conn:
        _insert_report(conn, "r1", "ws1", "run1")
    with engine.begin() as conn:
        with pytest.raises(sa.exc.IntegrityError):
            _insert_report(conn, "r2", "ws1", "run1")  # mesmo ws+run rejeitado
    with engine.begin() as conn:
        _insert_report(conn, "r3", "ws1", None)  # run NULL coexiste (índice parcial)
        _insert_report(conn, "r4", "ws1", None)


def test_upgrade_aborts_on_preexisting_duplicates(alembic_at_parent) -> None:
    engine, cfg = alembic_at_parent
    with engine.begin() as conn:
        _insert_report(conn, "d1", "ws1", "run1")
        _insert_report(conn, "d2", "ws1", "run1")

    with pytest.raises(RuntimeError, match="duplicado"):
        upgrade(cfg, TARGET_REVISION)


def test_downgrade_drops_index(alembic_at_parent) -> None:
    engine, cfg = alembic_at_parent
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        assert _index_sql(conn, INDEX_NAME) is None
