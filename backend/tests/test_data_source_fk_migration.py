"""FK ``pipeline_artifacts.data_source_id`` (ADR-278, revision adr278datasourcefk) —
única rede contra o ponto cego de FK do ``test_alembic_guardrails`` (``_diff_signature``
não emite signature p/ FK). Prova: (1) offline SQL Postgres contém ``NOT VALID`` +
``VALIDATE CONSTRAINT`` + ``ON DELETE SET NULL`` + nome explícito da constraint;
(2) SQLite é no-op (FK ausente; upgrade/downgrade não erram)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

pytestmark = pytest.mark.migration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
_REV_RANGE = "adr278datasource:adr278datasourcefk"
_REV_RANGE_DOWN = "adr278datasourcefk:adr278datasource"
_FK_NAME = "fk_pipeline_artifacts_data_source_id"


def _cfg_for(url: str, monkeypatch) -> Config:
    """Config alembic + injeta URL via settings (env.py sobrescreve sqlalchemy.url)."""
    monkeypatch.setenv("MATHOMS_DATABASE_URL", url)
    from backend.app.core import config as core_config

    monkeypatch.setattr(core_config.settings, "DATABASE_URL", url)
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_offline_sql_postgres_emits_not_valid_fk(monkeypatch, capsys):
    cfg = _cfg_for("postgresql://u:p@localhost/db", monkeypatch)
    command.upgrade(cfg, _REV_RANGE, sql=True)
    sql = capsys.readouterr().out.upper()
    assert _FK_NAME.upper() in sql
    assert "NOT VALID" in sql
    assert "VALIDATE CONSTRAINT" in sql
    assert "ON DELETE SET NULL" in sql


def test_offline_sql_postgres_downgrade_drops_constraint(monkeypatch, capsys):
    cfg = _cfg_for("postgresql://u:p@localhost/db", monkeypatch)
    command.downgrade(cfg, _REV_RANGE_DOWN, sql=True)
    sql = capsys.readouterr().out.upper()
    assert "DROP CONSTRAINT" in sql and _FK_NAME.upper() in sql


def test_sqlite_upgrade_downgrade_is_noop(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db", prefix="fk_mig_test_")
    os.close(fd)
    try:
        cfg = _cfg_for(f"sqlite+aiosqlite:///{path}", monkeypatch)
        command.upgrade(cfg, "adr278datasourcefk")
        engine = create_engine(f"sqlite:///{path}")
        fks = inspect(engine).get_foreign_keys("pipeline_artifacts")
        assert all(fk.get("name") != _FK_NAME for fk in fks), "FK não deve existir no SQLite"
        engine.dispose()
        command.downgrade(cfg, "adr278datasource")  # no-op no SQLite, não erra
    finally:
        Path(path).unlink(missing_ok=True)
