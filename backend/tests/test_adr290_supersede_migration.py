"""Tests da migration ``adr290supersede``: colunas ``thesis_key``/``superseded_at``/``superseded_by_run_id`` nullable + índice btree não-unique ``(workspace_id, thesis_key)`` (ADR-290 B1/B2); downgrade remove tudo."""

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

PARENT_REVISION = "adr279edges"
TARGET_REVISION = "adr290supersede"

NEW_COLUMNS = ("thesis_key", "superseded_at", "superseded_by_run_id")
THESIS_INDEX = "ix_sugagg_ws_thesis"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr290_test_")
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


def _suggestion_columns(conn) -> set[str]:
    rows = conn.execute(sa.text("PRAGMA table_info(suggestions)")).fetchall()
    return {row[1] for row in rows}


def _index_sql(conn, name: str) -> str | None:
    row = conn.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='index' AND name=:n"),
        {"n": name},
    ).fetchone()
    return row[0] if row else None


def test_upgrade_adds_columns_and_index(alembic_engine):
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    with engine.connect() as conn:
        cols = _suggestion_columns(conn)
        assert set(NEW_COLUMNS) <= cols, f"colunas ausentes: {set(NEW_COLUMNS) - cols}"
        idx_sql = _index_sql(conn, THESIS_INDEX)
        assert idx_sql is not None
        assert "UNIQUE" not in idx_sql.upper(), "índice deve ser não-unique (ADR-290 B2)"
        assert "workspace_id" in idx_sql and "thesis_key" in idx_sql


def test_upgrade_keeps_existing_rows_with_null_thesis(alembic_engine):
    """Sem backfill na migration: rows pré-existentes ficam thesis_key=NULL."""
    engine, cfg = alembic_engine
    # FK não enforçada em conexão SQLite crua (sem PRAGMA foreign_keys=ON) —
    # dispensa seed de workspaces/users.
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO suggestions (id, workspace_id, section_id, kind, origin, "
                "severity, title, rationale, dedup_key, status, created_at, updated_at) "
                "VALUES ('s-1', 'ws-1', 'S9', 'parecer_planejador', 'llm', 'warning', "
                "'t', 'r', 'k1', 'Pendente', '2026-06-12', '2026-06-12')"
            )
        )
    upgrade(cfg, TARGET_REVISION)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT thesis_key, superseded_at, superseded_by_run_id FROM suggestions")
        ).fetchone()
        assert row == (None, None, None)


def test_downgrade_removes_columns_and_index(alembic_engine):
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)
    with engine.connect() as conn:
        cols = _suggestion_columns(conn)
        assert not (set(NEW_COLUMNS) & cols), f"colunas não removidas: {set(NEW_COLUMNS) & cols}"
        assert _index_sql(conn, THESIS_INDEX) is None
