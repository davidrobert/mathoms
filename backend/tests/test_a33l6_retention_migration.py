"""Migration ``a33l6retention`` (A33.l6 · W6-T05): coluna ``retention_until``
em ``pipeline_artifacts`` + índice parcial ``WHERE retention_until IS NOT
NULL``. Upgrade adiciona coluna nullable sem default (rows existentes ficam
NULL ≡ fail-safe nunca-pruna); downgrade remove coluna e índice. Padrão:
``test_a32l5_prompt_version_migration.py``."""

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

PARENT_REVISION = "a32l5promptver"
TARGET_REVISION = "a33l6retention"
INDEX_NAME = "ix_pipeline_artifacts_retention_until"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="a33l6_test_")
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


def _index_names(conn, table: str) -> set[str]:
    rows = conn.execute(sa.text(f"PRAGMA index_list({table})")).fetchall()
    return {r[1] for r in rows}


def test_upgrade_adds_nullable_retention_until_and_partial_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.begin() as conn:
        assert "retention_until" not in _columns(conn, "pipeline_artifacts")
        assert INDEX_NAME not in _index_names(conn, "pipeline_artifacts")

    upgrade(cfg, TARGET_REVISION)

    with engine.begin() as conn:
        assert "retention_until" in _columns(conn, "pipeline_artifacts")
        assert INDEX_NAME in _index_names(conn, "pipeline_artifacts")
        # Nullable sem default: rows pré-migration ficam NULL (fail-safe
        # nunca-pruna) — o backfill roda dentro da task diária, nunca aqui.
        row = conn.execute(
            sa.text(
                "SELECT dflt_value, [notnull] FROM pragma_table_info('pipeline_artifacts') "
                "WHERE name='retention_until'"
            )
        ).fetchone()
        assert row is not None
        default_value, not_null = row
        assert default_value is None
        assert not_null == 0
        # Índice é parcial (WHERE retention_until IS NOT NULL) — a maioria
        # das rows é NULL (corrente/fail-safe).
        partial = conn.execute(
            sa.text("SELECT partial FROM pragma_index_list('pipeline_artifacts') WHERE name=:n"),
            {"n": INDEX_NAME},
        ).scalar()
        assert partial == 1


def test_downgrade_removes_retention_until_and_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.begin() as conn:
        assert "retention_until" not in _columns(conn, "pipeline_artifacts")
        assert INDEX_NAME not in _index_names(conn, "pipeline_artifacts")
