"""Migration ``adr279edges`` (ADR-279 · A25.l3): tabela derivada
``artifact_lineage_edge`` + índices ``(workspace_id, run_id)`` e
``(workspace_id, source_document_id)``. Upgrade cria tabela/índices; downgrade
dropa tudo (derivada/rebuildável — reversível trivial). FK Postgres-only de
``data_source_id`` não é assertável em SQLite (coluna plain por design)."""

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

PARENT_REVISION = "a170rtf00001"
TARGET_REVISION = "adr279edges"

_EXPECTED_COLUMNS = {
    "id",
    "workspace_id",
    "run_id",
    "src_stage",
    "src_key",
    "src_field",
    "dst_stage",
    "dst_key",
    "dst_field",
    "edge_type",
    "rule_ref",
    "source_document_id",
    "data_source_id",
    "winner",
}
_EXPECTED_INDEXES = {
    "ix_artifact_lineage_edge_ws_run",
    "ix_artifact_lineage_edge_ws_doc",
}


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr279_test_")
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


def _indexes(conn, table: str) -> set[str]:
    rows = conn.execute(sa.text(f"PRAGMA index_list({table})")).fetchall()
    return {r[1] for r in rows}


def test_upgrade_creates_edge_table_and_indexes(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert not _has_table(conn, "artifact_lineage_edge")

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        assert _has_table(conn, "artifact_lineage_edge")
        assert _columns(conn, "artifact_lineage_edge") == _EXPECTED_COLUMNS
        assert _EXPECTED_INDEXES.issubset(_indexes(conn, "artifact_lineage_edge"))


def test_downgrade_removes_edge_table(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        assert not _has_table(conn, "artifact_lineage_edge")
