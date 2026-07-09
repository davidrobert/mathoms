"""Migration ``adr324supersede`` (ADR-324): colunas ``superseded_at`` +
``superseded_by_id`` (FK self-ref ON DELETE SET NULL) em ``property_identity``.
Upgrade adiciona colunas nullable sem backfill (rows existentes ficam live);
downgrade remove ambas. Padrão: ``test_a33l6_retention_migration.py``."""

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

PARENT_REVISION = "a33l2ptax3112"
TARGET_REVISION = "adr324supersede"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr324_test_")
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
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def test_upgrade_adds_nullable_columns(alembic_engine):
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    with engine.connect() as conn:
        cols = _columns(conn, "property_identity")
        assert {"superseded_at", "superseded_by_id"} <= cols
        fks = conn.execute(sa.text("PRAGMA foreign_key_list(property_identity)")).fetchall()
        self_fks = [fk for fk in fks if fk[2] == "property_identity"]
        assert self_fks, "FK self-ref superseded_by_id ausente"
        assert self_fks[0][6] == "SET NULL"


def test_downgrade_removes_columns(alembic_engine):
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)
    with engine.connect() as conn:
        cols = _columns(conn, "property_identity")
        assert "superseded_at" not in cols
        assert "superseded_by_id" not in cols
