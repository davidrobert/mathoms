"""Tests para a migration ``adr362execrev`` — ADR-362 executor_revision."""

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

PARENT_REVISION = "adr324supersede"
TARGET_REVISION = "adr362execrev"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr362_test_")
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


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({table})"))}


def test_upgrade_adiciona_coluna_nullable(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert "executor_revision" not in _columns(conn, "pipeline_stage_logs")

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        info = {
            row[1]: row for row in conn.execute(sa.text("PRAGMA table_info(pipeline_stage_logs)"))
        }
    assert "executor_revision" in info
    # notnull == 0: row pré-migration não é backfilled (backfill fabricaria dado).
    assert info["executor_revision"][3] == 0


def test_downgrade_remove_a_coluna(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)
    with engine.connect() as conn:
        assert "executor_revision" not in _columns(conn, "pipeline_stage_logs")


def test_sem_indice_novo(alembic_engine) -> None:
    """A revisão é projeção, não filtro — índice entra quando houver query que filtre."""
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        before = {
            r[0] for r in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='index'"))
        }
    upgrade(cfg, TARGET_REVISION)
    with engine.connect() as conn:
        after = {
            r[0] for r in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='index'"))
        }
    assert after == before
