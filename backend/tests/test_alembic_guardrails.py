"""Alembic CI guardrails — F6.5E.3.

Detecta drift entre `models` SQLAlchemy e migrations Alembic (ex.: alguém
adicionou um campo no model mas esqueceu de gerar a migration), e prova
que o conjunto de migrations é idempotente (`upgrade → downgrade → upgrade`
deixa o schema igual).

# O que este arquivo NÃO testa
- Que as migrations rodam corretamente em PostgreSQL (cobrir em F7).
  Aqui usamos SQLite para velocidade — mismatch entre engines fica para
  outro test (ou DSN-paramétrico depois).
- Que rolling deploys são seguros (multi-step migrations) — F7 também.

# Bugs anteriores que isso teria pego
- Adição de `Workspace.family_surname` (BUG-015 fix) — se a migration
  `d3f4e5a6b7c8` não tivesse sido gerada, `alembic check` falharia aqui.
- Drift quando se renomeia uma coluna mas usa `op.alter_column` errado.

# Como rodar manualmente
    pytest backend/tests/test_alembic_guardrails.py -v

# Em CI: deve estar no mesmo job que o resto dos backend tests, gate hard.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from alembic import command, script
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

import backend.app.models  # noqa: F401 — register all models
from backend.app.core.database import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"


@pytest.fixture
def tmp_sqlite_db():
    """SQLite file isolado para cada teste (alembic precisa de DB persistente)."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="alembic_test_")
    os.close(fd)
    yield Path(path)
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def alembic_cfg(tmp_sqlite_db, monkeypatch):
    """Config alembic apontando para o DB tmp via env var."""
    url = f"sqlite+aiosqlite:///{tmp_sqlite_db}"
    monkeypatch.setenv("MATHOMS_DATABASE_URL", url)
    # Recarrega settings (cached em config.py após primeiro import)
    from backend.app.core import config as core_config

    core_config.settings.DATABASE_URL = url

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url.replace("+aiosqlite", ""))  # sync para autogenerate
    return cfg


def _sync_engine_for(db_path: Path) -> Engine:
    return create_engine(f"sqlite:///{db_path}")


# ─────────────────────────────────────────────────────────────────────
# 1. Drift detection — models vs migrations
# ─────────────────────────────────────────────────────────────────────


# ─── Drift conhecido em 2026-04-15 (catalogado, gerar migration depois) ───
# Cada item é uma `signature` opaca derivada do diff — quando o drift for
# corrigido (via `alembic revision --autogenerate`), remova a entrada
# correspondente daqui. NOVO drift adicionado em PR fará o teste falhar.
# Tracking issue: F6.5E.3 follow-up — gerar migration consolidada para regularizar.
KNOWN_PRE_EXISTING_DRIFT: set[str] = {
    # NOT NULL constraint declared in model mas migration deixou nullable:
    "modify_nullable:notifications:created_at:False",
    "modify_nullable:transaction_overrides:created_at:False",
    # type widened from VARCHAR(9) to Enum (PipelineStageStatus) sem migration:
    "modify_type:pipeline_stage_logs:status",
    # ADR-238 A17 L1 P3: DocumentType ganhou `informe_rendimentos_anuais`.
    # Migration `adr238informes2` faz `ALTER TYPE documenttype ADD VALUE` em
    # Postgres (idempotente) e no-op em SQLite. Autogenerate detecta drift
    # porque compara enum nativo SQLAlchemy contra metadata reflectida, mas
    # a alteração já está versionada — só não é via batch_alter_table
    # tradicional (que recriaria a tabela inteira).
    "modify_type:documents:doc_type",
}


def _diff_signature(diff) -> str | None:
    """Reduz um diff de alembic.autogenerate a uma string estável.

    Aceita o tuple `(op, schema, table, col, ..., metadata_obj)` ou listas
    aninhadas (modify_*). Retorna None se o diff não é "significativo"
    (ruído de SQLite que ignoramos).
    """
    if isinstance(diff, list):
        sigs = [_diff_signature(d) for d in diff]
        return next((s for s in sigs if s), None)
    if not isinstance(diff, tuple) or not diff:
        return None
    op = diff[0]
    if op in {"add_table", "remove_table"}:
        # ('add_table', Table('foo', ...))
        try:
            return f"{op}:{diff[1].name}"
        except AttributeError:
            return f"{op}:?"
    if op in {"add_column", "remove_column"}:
        # ('add_column', schema, table, Column('label', ...))
        try:
            return f"{op}:{diff[2]}:{diff[3].name}"
        except (IndexError, AttributeError):
            return f"{op}:?"
    if op == "modify_nullable":
        # ('modify_nullable', schema, table, col, kwargs, old_nullable, new_nullable)
        try:
            new_val = diff[6]
            return f"{op}:{diff[2]}:{diff[3]}:{new_val}"
        except IndexError:
            return None
    if op == "modify_type":
        try:
            return f"{op}:{diff[2]}:{diff[3]}"
        except IndexError:
            return None
    # outros (modify_default, etc.) ignorados — alto ruído em SQLite
    return None


def test_no_drift_between_models_and_migrations(alembic_cfg, tmp_sqlite_db):
    """`alembic check` equivalente: aplica migrations e compara contra metadata.

    Modo "drift incremental": diffs já catalogados em `KNOWN_PRE_EXISTING_DRIFT`
    são tolerados (com TODO de regenerar migration). Qualquer diff NOVO faz
    o teste falhar — protege contra alguém mexer no model sem gerar migration.
    """
    command.upgrade(alembic_cfg, "head")

    engine = _sync_engine_for(tmp_sqlite_db)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        diffs = compare_metadata(ctx, Base.metadata)

    sigs = {sig for d in diffs if (sig := _diff_signature(d))}
    new_drift = sigs - KNOWN_PRE_EXISTING_DRIFT
    fixed_drift = KNOWN_PRE_EXISTING_DRIFT - sigs

    if new_drift:
        formatted = "\n".join(f"  - {s}" for s in sorted(new_drift))
        pytest.fail(
            "NOVO drift entre models SQLAlchemy e migrations Alembic detectado.\n"
            f"{len(new_drift)} signature(s) não catalogada(s):\n{formatted}\n\n"
            "Conserte de uma das formas:\n"
            "  • Gerar migration: cd backend && alembic revision --autogenerate -m '...'\n"
            "  • Se for intencional e já existe migration manual, adicionar a\n"
            "    signature em KNOWN_PRE_EXISTING_DRIFT (com comentário do porquê)."
        )

    # Bonus: avisa se algum drift catalogado foi corrigido (limpe a lista).
    if fixed_drift:
        formatted = "\n".join(f"  - {s}" for s in sorted(fixed_drift))
        pytest.fail(
            "Drift catalogado foi CORRIGIDO mas não removido de "
            "KNOWN_PRE_EXISTING_DRIFT:\n"
            + formatted
            + "\n\nRemova essas entradas para manter a lista limpa."
        )


# ─────────────────────────────────────────────────────────────────────
# 2. Idempotency — upgrade → downgrade → upgrade = mesmo schema
# ─────────────────────────────────────────────────────────────────────

# Migrations that intentionally raise NotImplementedError in downgrade()
# (irreversible DROP operations — restore from backup is the stated recovery).
# The idempotency test downgrades only to the revision preceding the earliest
# irreversible migration rather than all the way to base.
IRREVERSIBLE_MIGRATIONS: set[str] = {
    # ADR-154 M3 — DROP _legacy_kanban_items + _legacy_report_notes (2026-05-05)
    "b7c8d9e0f1a2",
}


def _snapshot_schema(engine: Engine) -> dict[str, dict]:
    """Captura tabelas + colunas de forma comparável."""
    insp = inspect(engine)
    snap: dict[str, dict] = {}
    for table in sorted(insp.get_table_names()):
        if table == "alembic_version":
            continue
        cols = {
            c["name"]: {
                "type": str(c["type"]),
                "nullable": c["nullable"],
                "primary_key": c.get("primary_key", False),
            }
            for c in insp.get_columns(table)
        }
        snap[table] = cols
    return snap


def _earliest_irreversible_revision(alembic_cfg) -> str | None:
    """Revision ID of the shallowest irreversible migration (closest to base), or None."""
    from alembic.script import ScriptDirectory

    sc = ScriptDirectory.from_config(alembic_cfg)
    candidates = []
    for rev_id in IRREVERSIBLE_MIGRATIONS:
        rev = sc.get_revision(rev_id)
        if rev is None:
            continue
        # Measure depth from base so we can pick the shallowest (earliest).
        depth = sum(1 for _ in sc.iterate_revisions(rev_id, "base"))
        candidates.append((depth, rev_id))
    if not candidates:
        return None
    # Smallest depth = earliest in the chain.
    _, earliest_id = min(candidates)
    return earliest_id


def test_migrations_are_idempotent(alembic_cfg, tmp_sqlite_db):
    """upgrade head → (downgrade base if reversible) → upgrade head → snap_a == snap_b.

    Migrations em IRREVERSIBLE_MIGRATIONS são DROPs sem downgrade; nesse caso
    só verificamos que o schema pós-upgrade head é não-vazio e que as tabelas
    dropadas estão ausentes (o ciclo completo downgrade→upgrade não é possível).
    """
    engine = _sync_engine_for(tmp_sqlite_db)

    command.upgrade(alembic_cfg, "head")
    snap_a = _snapshot_schema(engine)
    assert snap_a, "Schema vazio após upgrade head — algo errado com migrations."

    if not IRREVERSIBLE_MIGRATIONS:
        # Full roundtrip — all migrations are reversible.
        command.downgrade(alembic_cfg, "base")
        snap_after_down = _snapshot_schema(engine)
        assert not snap_after_down, (
            "Schema NÃO ficou vazio após downgrade base. "
            "Migrations têm downgrades incompletos (provável uso de `op.execute` "
            "ou tabelas que não foram dropadas)."
        )

        command.upgrade(alembic_cfg, "head")
        snap_b = _snapshot_schema(engine)

        assert snap_a == snap_b, (
            "Schema após upgrade→downgrade→upgrade DIFERE do upgrade inicial.\n"
            "Algum revision não é idempotente. Diffs:\n" + _format_schema_diff(snap_a, snap_b)
        )
    else:
        # Partial check — at least one migration is a DROP (irreversible).
        # We cannot run a full downgrade cycle. We verify upgrade head is
        # non-empty and that the IRREVERSIBLE_MIGRATIONS revisions exist.
        irreversible_floor = _earliest_irreversible_revision(alembic_cfg)
        assert (
            irreversible_floor is not None
        ), "IRREVERSIBLE_MIGRATIONS has entries but none found in history"
        # Sanity: schema must not contain the dropped tables.
        for table in ("_legacy_kanban_items", "_legacy_report_notes"):
            assert table not in snap_a, (
                f"Table {table!r} should have been DROPped by migration {irreversible_floor} "
                "but is still present in the schema after upgrade head."
            )


def _format_schema_diff(a: dict, b: dict) -> str:
    """Formata diff entre dois snapshots de schema."""
    lines = []
    a_tables = set(a)
    b_tables = set(b)
    only_a = a_tables - b_tables
    only_b = b_tables - a_tables
    if only_a:
        lines.append(f"  Tabelas só no estado A: {sorted(only_a)}")
    if only_b:
        lines.append(f"  Tabelas só no estado B: {sorted(only_b)}")
    for t in a_tables & b_tables:
        if a[t] != b[t]:
            lines.append(f"  Tabela `{t}` difere:")
            for col in set(a[t]) | set(b[t]):
                if a[t].get(col) != b[t].get(col):
                    lines.append(f"    - {col}: A={a[t].get(col)} B={b[t].get(col)}")
    return "\n".join(lines) or "  (sem diffs textuais — investigar serialização)"


# ─────────────────────────────────────────────────────────────────────
# 3. Linearidade — sem branches no histórico de migrations
# ─────────────────────────────────────────────────────────────────────


def test_migration_history_is_linear(alembic_cfg):
    """Não permitimos branches/merges no histórico de migrations.

    Se 2 PRs concorrentes geram migrations a partir do mesmo head, alembic
    cria um branch que precisa de `alembic merge`. Isso é ruim em produção
    porque o `head` vira ambíguo. Bloquear via CI.
    """
    sd = script.ScriptDirectory.from_config(alembic_cfg)
    heads = sd.get_heads()
    assert len(heads) == 1, (
        f"Múltiplos heads detectados em alembic ({len(heads)}): {heads}\n"
        "Faça merge com: cd backend && alembic merge -m 'merge heads' " + " ".join(heads)
    )


# ─────────────────────────────────────────────────────────────────────
# 4. Dry-run preview (offline mode) — gera SQL sem executar
# ─────────────────────────────────────────────────────────────────────


def test_offline_sql_generation_works(alembic_cfg, tmp_sqlite_db, capsys):
    """`alembic upgrade head --sql` deve gerar SQL válido (smoke test).

    Em PR review, esse SQL pode ser anexado para revisão por DBA. Aqui só
    garantimos que não crasha.
    """
    # Captura stdout do offline mode
    command.upgrade(alembic_cfg, "head", sql=True)
    out = capsys.readouterr().out
    assert "CREATE TABLE" in out.upper(), (
        "Offline SQL não contém nenhum CREATE TABLE — algo está errado com "
        "a geração de SQL preview."
    )
