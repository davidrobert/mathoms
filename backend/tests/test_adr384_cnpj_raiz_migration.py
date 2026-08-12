"""Tests das migrations ``adr384cnpjraiz`` (DDL) + ``adr384cnpjseed`` (dados) — ADR-384."""

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

PARENT_REVISION = "adr378expira"
DDL_REVISION = "adr384cnpjraiz"
SEED_REVISION = "adr384cnpjseed"

# ADR-384 §Consequências — o gate vale sobre as MIGRATIONS (comparar DB de
# teste com o model é auto-referente); categorias emissoras exigem cnpj_raiz
# salvo entidade sem CNPJ BR (allowlist explícita, nunca silêncio).
_CATEGORIAS_EMISSORAS = ("bank", "broker", "exchange")
# bankofamerica: conta US sem entidade BR emissora; btgdigital: dupla
# derivação divergiu (CTVM × banco) — NULL até um informe real decidir.
_SEM_ENTIDADE_BR = frozenset({"bankofamerica", "btgdigital"})


def _alembic_config(async_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def alembic_engine(monkeypatch):
    fd, db_path_str = tempfile.mkstemp(suffix=".db", prefix="adr384_test_")
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
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({table})"))}


def test_upgrade_adiciona_coluna_index_e_check(alembic_engine) -> None:
    engine, cfg = alembic_engine
    with engine.connect() as conn:
        assert "cnpj_raiz" not in _columns(conn, "institution_catalog")
    upgrade(cfg, DDL_REVISION)
    with engine.connect() as conn:
        assert "cnpj_raiz" in _columns(conn, "institution_catalog")
        indexes = {
            row[1] for row in conn.execute(sa.text("PRAGMA index_list(institution_catalog)"))
        }
        assert "ix_institution_catalog_cnpj_raiz" in indexes


def test_check_rejeita_formato_invalido(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, DDL_REVISION)
    insert = sa.text(
        "INSERT INTO institution_catalog "
        "(id, code, name, category, tax_regime, metadata_json, cnpj_raiz, created_at, updated_at) "
        "VALUES (:id, :code, :name, 'bank', 'both', '{}', :cnpj, '2026-01-01', '2026-01-01')"
    )
    with engine.begin() as conn:
        conn.execute(insert, {"id": "t-ok", "code": "tok", "name": "T", "cnpj": "60701190"})
        conn.execute(insert, {"id": "t-null", "code": "tnull", "name": "T", "cnpj": None})
    for invalido in ("6070119", "607011901", "60.701.19", "6070119a"):
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    insert,
                    {"id": f"t-{invalido}", "code": f"t{invalido}", "name": "T", "cnpj": invalido},
                )


def test_downgrade_remove_coluna(alembic_engine) -> None:
    engine, cfg = alembic_engine
    upgrade(cfg, DDL_REVISION)
    downgrade(cfg, PARENT_REVISION)
    with engine.connect() as conn:
        assert "cnpj_raiz" not in _columns(conn, "institution_catalog")


def test_seed_cobre_toda_categoria_emissora(alembic_engine) -> None:
    """Gate ADR-384: todo code bank/broker/exchange tem cnpj_raiz pós-seed,
    salvo entidade sem CNPJ BR declarada na allowlist."""
    engine, cfg = alembic_engine
    upgrade(cfg, SEED_REVISION)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT code, cnpj_raiz FROM institution_catalog WHERE category IN "
                "('bank','broker','exchange')"
            )
        ).fetchall()
    assert rows, "seed não populou o catálogo"
    faltantes = {code for code, raiz in rows if not raiz} - _SEM_ENTIDADE_BR
    assert not faltantes, f"categoria emissora sem cnpj_raiz e fora da allowlist: {faltantes}"
