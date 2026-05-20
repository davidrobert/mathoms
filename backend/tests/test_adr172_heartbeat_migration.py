"""Tests para a migration ``adr172heartbeat`` — ADR-172 W2-T04."""

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

PARENT_REVISION = "adr229irpfprefill"
TARGET_REVISION = "adr172heartbeat"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr172_test_")
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


def _insert_run(conn, *, run_id: str, status: str, started_at: str) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO pipeline_runs "
            "(id, workspace_id, status, tier_at_run, reprocess_all, incremental, started_at) "
            "VALUES (:id, 'ws-1', :status, 'free', 0, 0, :started_at)"
        ),
        {"id": run_id, "status": status, "started_at": started_at},
    )


def _columns(conn, table: str) -> set[str]:
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return {row[1] for row in result}


def _index_sql(conn, name: str) -> str | None:
    row = conn.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='index' AND name=:n"),
        {"n": name},
    ).fetchone()
    return row[0] if row else None


def test_upgrade_adds_columns(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        before = _columns(conn, "pipeline_runs")
    assert "last_heartbeat_at" not in before
    assert "failure_reason" not in before

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        after = _columns(conn, "pipeline_runs")
    assert {"last_heartbeat_at", "failure_reason"}.issubset(after)


def test_upgrade_creates_partial_index_with_predicate(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        sql = _index_sql(conn, "ix_pipeline_runs_running_heartbeat")
    assert sql is not None
    assert "last_heartbeat_at" in sql
    assert "status='running'" in sql.replace('"', "").replace(" ", "")


def test_upgrade_backfills_heartbeat_for_running_runs(alembic_engine) -> None:
    engine, cfg = alembic_engine
    started = "2026-05-20 10:00:00"
    with engine.begin() as conn:
        _insert_run(conn, run_id="run-running", status="running", started_at=started)
        _insert_run(conn, run_id="run-completed", status="completed", started_at=started)

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT id, last_heartbeat_at FROM pipeline_runs ORDER BY id")
        ).fetchall()
    by_id = {row[0]: row[1] for row in rows}
    assert by_id["run-running"] == started
    assert by_id["run-completed"] is None


def test_downgrade_drops_columns_and_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        cols = _columns(conn, "pipeline_runs")
        idx_sql = _index_sql(conn, "ix_pipeline_runs_running_heartbeat")
    assert {"last_heartbeat_at", "failure_reason"}.isdisjoint(cols)
    assert idx_sql is None
