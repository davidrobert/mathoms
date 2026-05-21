"""Tests para a migration ``adr241index`` — índice composto pipeline_artifacts.

ADR-241 promove E2 a workspace-scoped, tornando ``_get_latest_in_workspace``
caminho quente. Sem índice composto ``(workspace_id, stage, artifact_key,
created_at)`` o ``ORDER BY created_at DESC LIMIT 1`` faz seq scan + sort.
"""

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

PARENT_REVISION = "adr238informes2"
TARGET_REVISION = "adr241index"
INDEX_NAME = "ix_pipeline_artifacts_ws_stage_key_created"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr241_test_")
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


def test_upgrade_creates_composite_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        before = _index_sql(conn, INDEX_NAME)
    assert before is None, "índice não deveria existir pré-upgrade"

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        after = _index_sql(conn, INDEX_NAME)
    assert after is not None, "índice deveria existir pós-upgrade"
    sql = after.lower()
    for col in ("workspace_id", "stage", "artifact_key", "created_at"):
        assert col in sql, f"índice deveria cobrir coluna {col}"


def test_downgrade_drops_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        sql = _index_sql(conn, INDEX_NAME)
    assert sql is None, "downgrade deveria remover o índice"
