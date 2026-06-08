"""Migration ``adr282overridenk`` (ADR-282 M1): colunas v2 + índice parcial em
``transaction_overrides``, puramente aditivas. Upgrade adiciona
``natural_key_hash``/``hash_version``/snapshot/``orphaned_at`` + ``ix_txov_ws_natural_key``;
downgrade remove tudo (reversível trivial)."""

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

PARENT_REVISION = "adr275auditidx"
TARGET_REVISION = "adr282overridenk"

NEW_COLUMNS = {
    "natural_key_hash",
    "hash_version",
    "tx_data",
    "tx_banco",
    "tx_titular",
    "tx_tipo_conta",
    "tx_valor_cents",
    "tx_moeda",
    "tx_direction",
    "tx_descricao",
    "orphaned_at",
}
INDEX_NAME = "ix_txov_ws_natural_key"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr282_test_")
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


def _columns(conn) -> set[str]:
    rows = conn.execute(sa.text("PRAGMA table_info(transaction_overrides)")).fetchall()
    return {r[1] for r in rows}


def _index_sql(conn, name: str) -> str | None:
    row = conn.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='index' AND name=:n"),
        {"n": name},
    ).fetchone()
    return row[0] if row else None


def test_upgrade_adds_v2_columns_and_partial_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert NEW_COLUMNS.isdisjoint(_columns(conn)), "colunas v2 não deveriam existir pré-upgrade"
        assert _index_sql(conn, INDEX_NAME) is None

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        assert NEW_COLUMNS.issubset(_columns(conn))
        idx_sql = _index_sql(conn, INDEX_NAME)
    assert idx_sql is not None
    lowered = idx_sql.lower()
    assert "workspace_id" in lowered and "natural_key_hash" in lowered
    assert "where" in lowered and "deleted_at is null" in lowered


def test_downgrade_removes_v2_columns_and_index(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        assert NEW_COLUMNS.isdisjoint(_columns(conn))
        assert _index_sql(conn, INDEX_NAME) is None
