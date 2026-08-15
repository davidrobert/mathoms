"""Migration ADR-387 PR2: snapshot no Report + hash_version na publicação."""

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
PARENT = "adr387pr1src"
REVISION = "adr387pr2snap"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr387pr2_")
    os.close(fd)
    db_path = Path(db_path_str)
    async_url = f"sqlite+aiosqlite:///{db_path}"
    monkeypatch.setenv("MATHOMS_DATABASE_URL", async_url)
    from backend.app.core import config as core_config

    core_config.settings.DATABASE_URL = async_url
    cfg = _alembic_config(async_url)
    upgrade(cfg, PARENT)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    yield engine, cfg
    engine.dispose()
    db_path.unlink(missing_ok=True)


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({table})"))}


def test_upgrade_adiciona_snapshot_e_hash_version(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert "protection_snapshot_json" not in _columns(conn, "reports")
        assert "hash_version" not in _columns(conn, "report_publications")
    upgrade(cfg, REVISION)
    with engine.connect() as conn:
        assert "protection_snapshot_json" in _columns(conn, "reports")
        assert "report_id" in _columns(conn, "report_publications")
        assert "hash_version" in _columns(conn, "report_publications")


def test_downgrade_remove_colunas(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, REVISION)
    downgrade(cfg, PARENT)
    with engine.connect() as conn:
        assert "protection_snapshot_json" not in _columns(conn, "reports")
        assert "hash_version" not in _columns(conn, "report_publications")
