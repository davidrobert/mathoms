"""Migration ``adr278datasource`` (ADR-278): tabela ``data_source`` + coluna
``pipeline_artifacts.data_source_id`` (aditivo). Upgrade cria tabela/coluna/índices;
downgrade remove tudo (reversível trivial). Backfill roda em DB vazio = no-op seguro."""

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

PARENT_REVISION = "adr282overridenk"
TARGET_REVISION = "adr278datasource"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr278_test_")
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


def _has_table(conn, name: str) -> bool:
    row = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"), {"n": name}
    ).fetchone()
    return row is not None


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def test_upgrade_creates_data_source_and_column(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert not _has_table(conn, "data_source")
        assert "data_source_id" not in _columns(conn, "pipeline_artifacts")

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        assert _has_table(conn, "data_source")
        assert {"institution_code", "external_account_ref", "kind", "display_name"}.issubset(
            _columns(conn, "data_source")
        )
        assert "data_source_id" in _columns(conn, "pipeline_artifacts")


def test_downgrade_removes_data_source_and_column(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        assert not _has_table(conn, "data_source")
        assert "data_source_id" not in _columns(conn, "pipeline_artifacts")
