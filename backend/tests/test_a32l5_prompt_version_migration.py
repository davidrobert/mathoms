"""Migration ``a32l5promptver`` (ADR-311): coluna ``prompt_version`` em
``pipeline_artifacts``. Upgrade adiciona coluna nullable (rows existentes
ficam NULL ≡ versão desconhecida/0, sem backfill de conteúdo); downgrade
remove. Padrão: ``test_adr278_data_source_migration.py``."""

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

PARENT_REVISION = "a31l1opsaudit"
TARGET_REVISION = "a32l5promptver"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="a32l5_test_")
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


def test_upgrade_adds_prompt_version_and_preexisting_rows_stay_null(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.begin() as conn:
        assert "prompt_version" not in _columns(conn, "pipeline_artifacts")

    upgrade(cfg, TARGET_REVISION)

    with engine.begin() as conn:
        assert "prompt_version" in _columns(conn, "pipeline_artifacts")
        # Coluna nullable sem default: rows pré-migration ficam NULL (≡ versão 0).
        row = conn.execute(
            sa.text(
                "SELECT dflt_value, [notnull] FROM pragma_table_info('pipeline_artifacts') WHERE name='prompt_version'"
            )
        ).fetchone()
        assert row is not None
        default_value, not_null = row
        assert default_value is None
        assert not_null == 0


def test_downgrade_removes_prompt_version(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.begin() as conn:
        assert "prompt_version" not in _columns(conn, "pipeline_artifacts")
