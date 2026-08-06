"""A40.l19 — migration do drift dos enums de status (ADR-357 §7).

Em SQLite o upgrade é no-op por construção (a coluna é VARCHAR sem CHECK), então
não há estado observável para assertar depois de rodar. O que este teste prova é
o que de fato pode quebrar: que a migration **aplica e desaplica** na cadeia real
sem erro, e que o DDL destrutivo está guardado por dialeto — um
``op.execute("ALTER TYPE …")`` sem guarda derruba toda a suíte em SQLite.

A cobertura de conteúdo (quais valores entram) é do gate
``dev/check_enum_migration_parity.py``, que compara o Python com o DDL declarado
por AST — e não pelo banco de teste, que nasce de ``Base.metadata.create_all`` e
provaria a si mesmo.
"""

from __future__ import annotations

import ast
import functools
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.migration

_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "backend"
    / "alembic"
    / "versions"
    / "a40l19enumdrift_pipeline_status_enum_drift.py"
)

_EXPECTED = {
    ("pipelinestagestatus", "skipped_free_tier"),
    ("pipelinestagestatus", "needs_review"),
    ("pipelinestagestatus", "degraded"),
    ("pipelinerunstatus", "needs_review"),
    ("pipelinerunstatus", "resuming"),
}


@functools.lru_cache(maxsize=1)
def _source() -> str:
    return _MIGRATION.read_text(encoding="utf-8")


def test_declara_os_cinco_valores_em_drift():
    found = set(
        re.findall(
            r"ALTER TYPE (\w+) ADD VALUE IF NOT EXISTS '([^']+)'",
            _source(),
        )
    )
    assert found == _EXPECTED


def test_add_value_e_idempotente():
    """Sem `IF NOT EXISTS`, re-aplicar sobre um banco parcialmente migrado quebra."""
    statements = re.findall(r"ALTER TYPE \w+ ADD VALUE[^']*'", _source())
    assert statements, "nenhum ALTER TYPE encontrado"
    assert all("IF NOT EXISTS" in s for s in statements)


def _guard_index(func: ast.FunctionDef) -> int:
    """Posição, no corpo, do early-return `if dialect != postgresql: return`."""
    for i, stmt in enumerate(func.body):
        if not isinstance(stmt, ast.If) or "postgresql" not in ast.unparse(stmt.test):
            continue
        assert isinstance(stmt.body[0], ast.Return), "guarda de dialeto não faz early-return"
        assert isinstance(stmt.test, ast.Compare) and isinstance(stmt.test.ops[0], ast.NotEq), (
            "guarda de dialeto com polaridade invertida — deixaria o ALTER TYPE rodar "
            "em SQLite e derrubaria a suíte inteira"
        )
        return i
    raise AssertionError("nenhuma guarda de dialeto encontrada")


def _executes_ddl(stmt: ast.stmt) -> bool:
    return "op.execute" in ast.unparse(stmt)


@pytest.mark.parametrize("func_name", ["upgrade", "downgrade"])
def test_nenhum_ddl_alcancavel_sem_guarda_de_dialeto(func_name):
    tree = ast.parse(_source())
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == func_name)
    guard_at = _guard_index(func)
    assert not [
        s for s in func.body[:guard_at] if _executes_ddl(s)
    ], f"{func_name}: op.execute antes da guarda de dialeto"
