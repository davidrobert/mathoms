"""Tests da migration ``a31l1opsaudit`` — cria internal_ops_audit + meta-linha de corte (ADR-309)."""

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

PARENT_REVISION = "a17l4itausa"
TARGET_REVISION = "a31l1opsaudit"
TABLE = "internal_ops_audit"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="a31l1_test_")
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


def test_upgrade_creates_table_and_cutover_row(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    with engine.connect() as conn:
        assert _table_exists(conn, TABLE)
        rows = conn.execute(
            sa.text(f"SELECT action, actor, result FROM {TABLE}")  # noqa: S608 — nome fixo
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "audit.migration"
    assert rows[0][1] == "alembic:a31l1opsaudit"
    assert rows[0][2] == "ok"


def test_downgrade_drops_table(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)
    with engine.connect() as conn:
        assert not _table_exists(conn, TABLE)
