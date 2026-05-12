"""ADR-180 follow-up — migration ``d2c3d4e5f6a7`` close orphan goals."""

from __future__ import annotations

import importlib
import os
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend.app.models.goal import VALID_GOAL_TYPES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"

migration = importlib.import_module(
    "backend.alembic.versions.d2c3d4e5f6a7_adr180_close_orphan_goal_types"
)


def test_hardcoded_types_match_current_contract():
    """Snapshot A10.6 deve refletir o contrato atual no model."""
    assert set(migration._VALID_GOAL_TYPES_A10_6) == VALID_GOAL_TYPES, (
        "Snapshot A10.6 divergiu de VALID_GOAL_TYPES — se a divergência foi "
        "intencional (novo tipo adicionado), escreva nova migration de cleanup "
        "para fechar rows órfãs do contrato atual. NÃO altere o snapshot desta "
        "migration: migrations devem ser determinísticas."
    )


@pytest.fixture
def tmp_sqlite_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="alembic_orphan_goals_")
    os.close(fd)
    yield Path(path)
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def alembic_cfg(tmp_sqlite_db, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_sqlite_db}"
    monkeypatch.setenv("MATHOMS_DATABASE_URL", url)
    from backend.app.core import config as core_config

    core_config.settings.DATABASE_URL = url
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url.replace("+aiosqlite", ""))
    return cfg


def _insert_goal(conn, ws_id: str, goal_type: str, *, effective_to: date | None = None) -> str:
    goal_id = str(uuid.uuid4())
    conn.execute(
        text(
            "INSERT INTO goals (id, workspace_id, type, params_json, derived_json, "
            "effective_from, effective_to, is_template, created_at, updated_at) "
            "VALUES (:id, :ws, :t, '{}', '{}', :ef, :et, 0, :now, :now)"
        ),
        {
            "id": goal_id,
            "ws": ws_id,
            "t": goal_type,
            "ef": date(2026, 1, 1).isoformat(),
            "et": effective_to.isoformat() if effective_to else None,
            "now": datetime.now(timezone.utc).isoformat(),
        },
    )
    return goal_id


def _read_effective_to(engine, goal_id: str) -> str | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT effective_to FROM goals WHERE id = :id"), {"id": goal_id}
        ).fetchone()
    return row.effective_to


def test_migration_closes_orphan_and_preserves_canonical(alembic_cfg, tmp_sqlite_db):
    """Orfãs vigentes são fechadas; canônicas e já-fechadas ficam intactas."""
    command.upgrade(alembic_cfg, "c9d0e1f2a3b4")
    engine = create_engine(f"sqlite:///{tmp_sqlite_db}")
    ws_id = str(uuid.uuid4())
    # SQLite não enforça FKs por default; inserções diretas isolam a lógica da migration.
    with engine.begin() as conn:
        orphan_id = _insert_goal(conn, ws_id, "PLANNING_CONTEXT")
        canonical_id = _insert_goal(conn, ws_id, "INDEPENDENCIA_FINANCEIRA")
        closed_id = _insert_goal(conn, ws_id, "BUDGET_CEILING", effective_to=date(2026, 4, 1))

    command.upgrade(alembic_cfg, "head")

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert _read_effective_to(engine, orphan_id) == yesterday
    assert _read_effective_to(engine, canonical_id) is None
    assert _read_effective_to(engine, closed_id) == "2026-04-01"


def test_migration_is_idempotent(alembic_cfg, tmp_sqlite_db):
    """Após migration aplicada, re-rodar o UPDATE não fecha rows canônicas."""
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(f"sqlite:///{tmp_sqlite_db}")
    ws_id = str(uuid.uuid4())
    with engine.begin() as conn:
        canonical_id = _insert_goal(conn, ws_id, "APORTE_MENSAL")

    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE goals SET effective_to = :ef "
                "WHERE effective_to IS NULL AND type NOT IN "
                "('INDEPENDENCIA_FINANCEIRA', 'APORTE_MENSAL', 'DOLARIZACAO', 'ALOCACAO_ALVO')"
            ),
            {"ef": date.today().isoformat()},
        )
        assert result.rowcount == 0
    assert _read_effective_to(engine, canonical_id) is None
