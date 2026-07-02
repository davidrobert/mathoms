"""Migration ``a20l12semver`` — remap prompt_version legado→semver puro +
colunas ``prompt_version_legacy``/``confidence``/``needs_review`` (A20.l12)."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.command import downgrade, upgrade
from alembic.config import Config

pytestmark = pytest.mark.migration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
ALEMBIC_DIR = PROJECT_ROOT / "backend" / "alembic"

PARENT_REVISION = "adr173budgetnull"
TARGET_REVISION = "a20l12semver"


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_at_parent(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="a20l12_test_")
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


def _seed_call_log(conn, prompt_version: str) -> str:
    user_id, ws_id, row_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    conn.execute(
        sa.text(
            "INSERT INTO users (id, email, hashed_password, full_name, is_active, created_at) "
            "VALUES (:id, :email, 'x', 'U', 1, CURRENT_TIMESTAMP)"
        ),
        {"id": user_id, "email": f"{user_id[:8]}@t.com"},
    )
    conn.execute(
        sa.text(
            "INSERT INTO workspaces (id, name, owner_id, created_at) "
            "VALUES (:id, 'WS', :owner, CURRENT_TIMESTAMP)"
        ),
        {"id": ws_id, "owner": user_id},
    )
    conn.execute(
        sa.text(
            "INSERT INTO llm_call_log "
            "(id, workspace_id, stage, model_name, prompt_version, tokens_in, tokens_out, "
            " cost_usd, cost_known, duration_ms, created_at) "
            "VALUES (:id, :ws, 'E1.6', 'claude-test', :pv, 10, 5, 0.01, 1, 100, CURRENT_TIMESTAMP)"
        ),
        {"id": row_id, "ws": ws_id, "pv": prompt_version},
    )
    conn.commit()
    return row_id


def _row(conn, row_id: str):
    return conn.execute(
        sa.text(
            "SELECT prompt_version, prompt_version_legacy FROM llm_call_log WHERE id = :id"
        ),
        {"id": row_id},
    ).fetchone()


def test_upgrade_remapeia_legado_e_preserva_original(alembic_at_parent) -> None:
    engine, cfg = alembic_at_parent
    with engine.connect() as conn:
        legacy_id = _seed_call_log(conn, "e16-v1.1.2")
        pure_id = _seed_call_log(conn, "2.1.0")

    upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        legacy = _row(conn, legacy_id)
        pure = _row(conn, pure_id)
    assert legacy == ("1.1.2", "e16-v1.1.2")
    assert pure == ("2.1.0", None)


def test_downgrade_restaura_valor_legado(alembic_at_parent) -> None:
    engine, cfg = alembic_at_parent
    with engine.connect() as conn:
        legacy_id = _seed_call_log(conn, "informe-prev-v1.1.0")

    upgrade(cfg, TARGET_REVISION)
    downgrade(cfg, PARENT_REVISION)

    with engine.connect() as conn:
        value = conn.execute(
            sa.text("SELECT prompt_version FROM llm_call_log WHERE id = :id"),
            {"id": legacy_id},
        ).scalar_one()
    assert value == "informe-prev-v1.1.0"
