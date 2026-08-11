"""Tests da migration ``adr376expira``: colunas ``horizon``/``pipeline_run_id`` nullable, FKs SET NULL para pipeline_runs, e swap do UNIQUE full ``uq_sugagg_ws_dedup_status`` pelo índice único parcial ``uq_sugagg_ws_dedup_ativa`` (ADR-376 §D1/§D3/§D4); recreate do batch preserva as FKs de saída (revisão senior-cto A-2); downgrade dedup-a e restaura o full unique."""

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

PARENT_REVISION = "a40l20parecerout"
TARGET_REVISION = "adr376expira"

NEW_COLUMNS = ("horizon", "pipeline_run_id")
PARTIAL_UNIQUE = "uq_sugagg_ws_dedup_ativa"

# FKs de saída que o recreate do batch_alter_table DEVE preservar
# (coluna → (tabela alvo, ondelete)).
OUTBOUND_FKS = {
    "workspace_id": ("workspaces", "CASCADE"),
    "report_id": ("reports", "SET NULL"),
    "accepted_decision_id": ("decisions", "SET NULL"),
}


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr376_test_")
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


def _table_sql(conn) -> str:
    row = conn.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='suggestions'")
    ).fetchone()
    return row[0]


def _fk_map(conn) -> dict[str, tuple[str, str]]:
    """coluna → (tabela alvo, on_delete) via PRAGMA foreign_key_list."""
    rows = conn.execute(sa.text("PRAGMA foreign_key_list(suggestions)")).fetchall()
    # colunas do pragma: id, seq, table, from, to, on_update, on_delete, match
    return {row[3]: (row[2], row[6]) for row in rows}


def _seed_row(conn, *, sid: str, dedup: str, status: str) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO suggestions (id, workspace_id, section_id, kind, origin, "
            "severity, title, rationale, dedup_key, status, created_at, updated_at) "
            f"VALUES ('{sid}', 'ws-1', 'S3', 'parecer_planejador', 'llm', 'warning', "
            f"'t', 'r', '{dedup}', '{status}', '2026-06-12', '2026-06-12')"
        )
    )


def test_upgrade_adds_columns_and_partial_unique(alembic_engine):
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    with engine.connect() as conn:
        cols = _suggestion_columns(conn)
        assert set(NEW_COLUMNS) <= cols, f"colunas ausentes: {set(NEW_COLUMNS) - cols}"
        idx_sql = _index_sql(conn, PARTIAL_UNIQUE)
        assert idx_sql is not None
        assert "UNIQUE" in idx_sql.upper()
        assert "WHERE" in idx_sql.upper(), "índice deve ser parcial (ADR-376 §D3)"
        for status in ("Pendente", "Aceita", "Modificada"):
            assert status in idx_sql
        assert "uq_sugagg_ws_dedup_status" not in _table_sql(conn)


def test_upgrade_preserves_outbound_fks(alembic_engine):
    """Recreate do batch não pode perder FK nem ondelete (senior-cto A-2 / ADR-371)."""
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    with engine.connect() as conn:
        fks = _fk_map(conn)
        for col, (target, ondelete) in OUTBOUND_FKS.items():
            assert col in fks, f"FK perdida no recreate: {col}"
            assert fks[col] == (target, ondelete), f"{col}: {fks[col]} != {(target, ondelete)}"
        for col in ("pipeline_run_id", "superseded_by_run_id"):
            assert fks.get(col) == ("pipeline_runs", "SET NULL"), f"FK nova ausente: {col}"


def test_upgrade_allows_duplicate_superseded(alembic_engine):
    """Razão de existir da migration: mesma dedup_key 2× em Superseded não viola; 2ª Pendente ativa com mesma key continua violando."""
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    with engine.begin() as conn:
        _seed_row(conn, sid="s-1", dedup="k1", status="Superseded")
        _seed_row(conn, sid="s-2", dedup="k1", status="Superseded")
        _seed_row(conn, sid="s-3", dedup="k1", status="Pendente")
    with engine.connect() as conn:
        with pytest.raises(sa.exc.IntegrityError):
            with conn.begin():
                _seed_row(conn, sid="s-4", dedup="k1", status="Pendente")


def test_downgrade_dedups_and_restores_full_unique(alembic_engine):
    """Downgrade destrutivo-documentado: remove duplicatas (ws,dedup,status) mantendo a mais recente e recria o UNIQUE full."""
    engine, cfg = alembic_engine
    upgrade(cfg, TARGET_REVISION)
    with engine.begin() as conn:
        _seed_row(conn, sid="s-1", dedup="k1", status="Superseded")
        _seed_row(conn, sid="s-2", dedup="k1", status="Superseded")
    downgrade(cfg, PARENT_REVISION)
    with engine.connect() as conn:
        cols = _suggestion_columns(conn)
        assert not (set(NEW_COLUMNS) & cols), f"colunas não removidas: {set(NEW_COLUMNS) & cols}"
        assert _index_sql(conn, PARTIAL_UNIQUE) is None
        assert "uq_sugagg_ws_dedup_status" in _table_sql(conn)
        remaining = conn.execute(
            sa.text("SELECT id FROM suggestions WHERE dedup_key='k1'")
        ).fetchall()
        assert [row[0] for row in remaining] == ["s-2"], "dedup deve manter a row mais recente"
