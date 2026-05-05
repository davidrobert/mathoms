"""Tests para a migration q5r6s7t8u9v0 — rename stage identifiers (ADR-093 F9.3)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
ALEMBIC_DIR = PROJECT_ROOT / "backend" / "alembic"

# Revision that creates pipeline_artifacts + pipeline_stage_logs (parent).
PARENT_REVISION = "p4q5r6s7t8u9"
TARGET_REVISION = "q5r6s7t8u9v0"


@pytest.fixture
def alembic_engine(monkeypatch):
    """SQLite file + Alembic config upgraded to PARENT_REVISION.

    Pattern mirrors test_alembic_guardrails.py: inject MATHOMS_DATABASE_URL
    + patch settings so env.py sees the test DB, not the production one.
    Yields (sync_engine, alembic_cfg).
    """
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="f93_test_")
    os.close(fd)
    db_path = Path(db_path_str)

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sync_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("MATHOMS_DATABASE_URL", async_url)

    from backend.app.core import config as core_config

    core_config.settings.DATABASE_URL = async_url

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)

    upgrade(cfg, PARENT_REVISION)

    engine = sa.create_engine(sync_url)
    yield engine, cfg

    engine.dispose()
    try:
        db_path.unlink()
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_artifact(conn, stage: str, run_id: str = "run-1") -> None:
    conn.execute(
        sa.text(
            "INSERT INTO pipeline_artifacts "
            "(workspace_id, pipeline_run_id, stage, artifact_key, content_json, created_at) "
            "VALUES ('ws-1', :run_id, :stage, 'key-1', '{}', CURRENT_TIMESTAMP)"
        ),
        {"stage": stage, "run_id": run_id},
    )


def _insert_stage_log(conn, stage: str) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO pipeline_stage_logs "
            "(id, pipeline_run_id, stage, status, started_at) "
            "VALUES (:id, 'run-1', :stage, 'success', CURRENT_TIMESTAMP)"
        ),
        {"id": f"log-{stage}", "stage": stage},
    )


def _stages_in_artifacts(conn) -> set[str]:
    result = conn.execute(sa.text("SELECT DISTINCT stage FROM pipeline_artifacts"))
    return {row[0] for row in result}


def _stages_in_logs(conn) -> set[str]:
    result = conn.execute(sa.text("SELECT DISTINCT stage FROM pipeline_stage_logs"))
    return {row[0] for row in result}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_upgrade_renames_pipeline_artifacts_rows(alembic_engine):
    engine, cfg = alembic_engine

    with engine.begin() as conn:
        _insert_artifact(conn, "E3", run_id="run-1")
        _insert_artifact(conn, "E5", run_id="run-2")
        _insert_artifact(conn, "E5.N", run_id="run-3")

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        stages = _stages_in_artifacts(conn)

    assert "reconcile_transactions" in stages
    assert "analyze_finances" in stages
    assert "generate_narratives" in stages
    assert "E3" not in stages
    assert "E5" not in stages
    assert "E5.N" not in stages


def test_upgrade_renames_pipeline_stage_logs_rows(alembic_engine):
    engine, cfg = alembic_engine

    with engine.begin() as conn:
        _insert_stage_log(conn, "E3")
        _insert_stage_log(conn, "E5")
        _insert_stage_log(conn, "E5.N")

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        stages = _stages_in_logs(conn)

    assert "reconcile_transactions" in stages
    assert "analyze_finances" in stages
    assert "generate_narratives" in stages
    assert "E3" not in stages
    assert "E5" not in stages
    assert "E5.N" not in stages


def test_upgrade_aborts_on_unknown_stage(alembic_engine):
    engine, cfg = alembic_engine

    with engine.begin() as conn:
        _insert_artifact(conn, "E99-fake")

    with pytest.raises(RuntimeError, match="Unknown stage values"):
        upgrade(cfg, TARGET_REVISION)


def test_upgrade_is_idempotent(alembic_engine):
    engine, cfg = alembic_engine

    with engine.begin() as conn:
        _insert_artifact(conn, "E3")

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        stages_after_first = _stages_in_artifacts(conn)

    # Second upgrade is a no-op — descriptive names don't match legacy keys.
    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        stages_after_second = _stages_in_artifacts(conn)

    assert stages_after_first == stages_after_second
    assert "reconcile_transactions" in stages_after_second


def test_downgrade_restores_legacy_names(alembic_engine):
    engine, cfg = alembic_engine

    with engine.begin() as conn:
        _insert_artifact(conn, "E3")
        _insert_stage_log(conn, "E5")

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        assert "reconcile_transactions" in _stages_in_artifacts(conn)
        assert "analyze_finances" in _stages_in_logs(conn)

    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        artifact_stages = _stages_in_artifacts(conn)
        log_stages = _stages_in_logs(conn)

    assert "E3" in artifact_stages
    assert "reconcile_transactions" not in artifact_stages
    assert "E5" in log_stages
    assert "analyze_finances" not in log_stages
