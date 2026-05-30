"""Tests da migration ``adr274auditidx``: índices compostos ``(workspace_id, created_at)`` e ``(actor_user_id, created_at)`` cobrem ``WHERE <col>=? ORDER BY created_at DESC`` (caminho quente de leitura ADR-274 l7); o single-col ``ix_audit_logs_created_at`` é removido (redundante)."""

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

PARENT_REVISION = "adr272reviewreasons"
TARGET_REVISION = "adr274auditidx"

WS_INDEX = "ix_audit_logs_workspace_created"
ACTOR_INDEX = "ix_audit_logs_actor_created"
OLD_INDEX = "ix_audit_logs_created_at"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr274_test_")
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


def test_upgrade_creates_composite_indexes_and_drops_single(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert _index_sql(conn, OLD_INDEX) is not None, "single-col deveria existir pré-upgrade"
        assert _index_sql(conn, WS_INDEX) is None
        assert _index_sql(conn, ACTOR_INDEX) is None

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        ws_sql = _index_sql(conn, WS_INDEX)
        actor_sql = _index_sql(conn, ACTOR_INDEX)
        assert _index_sql(conn, OLD_INDEX) is None, "single-col deveria ser removido"
    assert (
        ws_sql is not None and "workspace_id" in ws_sql.lower() and "created_at" in ws_sql.lower()
    )
    assert (
        actor_sql is not None
        and "actor_user_id" in actor_sql.lower()
        and "created_at" in actor_sql.lower()
    )


def test_downgrade_restores_single_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        assert _index_sql(conn, OLD_INDEX) is not None, "downgrade deveria restaurar single-col"
        assert _index_sql(conn, WS_INDEX) is None
        assert _index_sql(conn, ACTOR_INDEX) is None
