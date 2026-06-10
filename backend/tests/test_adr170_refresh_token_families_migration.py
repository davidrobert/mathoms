"""Tests para a migration ``a170rtf00001`` — ADR-170 W3-T03."""

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

PARENT_REVISION = "f2a3b4c5d6e7"
TARGET_REVISION = "a170rtf00001"

EXPECTED_COLUMNS = {
    "id",
    "user_id",
    "token_hash",
    "token_version_at_issue",
    "prev_token_hash",
    "prev_rotated_at",
    "rotation_count",
    "created_at",
    "last_used_at",
    "expires_at",
    "revoked_at",
}


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr170_test_")
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


def test_upgrade_creates_table_with_expected_columns(alembic_engine):
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    inspector = sa.inspect(engine)
    assert "refresh_token_families" in inspector.get_table_names()
    cols = {c["name"] for c in inspector.get_columns("refresh_token_families")}
    assert cols == EXPECTED_COLUMNS
    indexes = {ix["name"] for ix in inspector.get_indexes("refresh_token_families")}
    assert "ix_refresh_token_families_user_id" in indexes


def test_downgrade_drops_table(alembic_engine):
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)
    inspector = sa.inspect(engine)
    assert "refresh_token_families" not in inspector.get_table_names()
