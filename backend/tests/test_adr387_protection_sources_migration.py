"""Migration ADR-387 PR1: fontes relacionais do snapshot de proteção."""

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

PARENT_REVISION = "adr384cnpjseed"
REVISION = "adr387pr1src"

_NEW_TABLES = frozenset(
    {
        "family_member_protection_profiles",
        "economic_dependencies",
        "protection_income_declarations",
        "family_member_tax_profiles",
        "fiscal_rule_sets",
    }
)
_NEW_PROTECTION_COLUMNS = frozenset(
    {
        "insured_family_member_id",
        "benefit_mode",
        "benefit_monthly_brl_cents",
    }
)


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr387_test_")
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


def _tables(conn) -> set[str]:
    rows = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    return {row[0] for row in rows}


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({table})"))}


def test_upgrade_cria_fontes_e_colunas_de_beneficio(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert _NEW_TABLES.isdisjoint(_tables(conn))
        assert _NEW_PROTECTION_COLUMNS.isdisjoint(_columns(conn, "protections"))
    upgrade(cfg, REVISION)
    with engine.connect() as conn:
        assert set(_NEW_TABLES).issubset(_tables(conn))
        assert set(_NEW_PROTECTION_COLUMNS).issubset(_columns(conn, "protections"))


def test_downgrade_remove_fontes_e_colunas(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, REVISION)
    downgrade(cfg, PARENT_REVISION)
    with engine.connect() as conn:
        assert _NEW_TABLES.isdisjoint(_tables(conn))
        assert _NEW_PROTECTION_COLUMNS.isdisjoint(_columns(conn, "protections"))


def test_benefit_mode_check_esta_no_schema(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, REVISION)
    with engine.connect() as conn:
        ddl = conn.execute(
            sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='protections'")
        ).scalar_one()
    assert "lump_sum" in ddl
    assert "monthly_income" in ddl
    assert "chk_protection_benefit_mode" in ddl
