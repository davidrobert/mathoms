"""Tests para a migration ``adr272reviewreasons`` — cria review_reasons + índice composto (workspace_id, pipeline_run_id, code). Sem backfill (ADR-272)."""

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

PARENT_REVISION = "adr269tsdedup"
TARGET_REVISION = "adr272reviewreasons"
TABLE = "review_reasons"
COMPOSITE_INDEX = "ix_review_reasons_ws_run_code"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr272_test_")
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


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone()
    return row is not None


def _index_sql(conn, name: str) -> str | None:
    row = conn.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='index' AND name=:n"),
        {"n": name},
    ).fetchone()
    return row[0] if row else None


def test_upgrade_creates_table_and_composite_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert not _table_exists(conn, TABLE), "tabela não deveria existir pré-upgrade"

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        assert _table_exists(conn, TABLE), "tabela deveria existir pós-upgrade"
        sql = _index_sql(conn, COMPOSITE_INDEX)
    assert sql is not None, "índice composto deveria existir pós-upgrade"
    lowered = sql.lower()
    for col in ("workspace_id", "pipeline_run_id", "code"):
        assert col in lowered, f"índice deveria cobrir {col}"


def test_downgrade_drops_table(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        assert not _table_exists(conn, TABLE), "downgrade deveria remover a tabela"
        assert _index_sql(conn, COMPOSITE_INDEX) is None
