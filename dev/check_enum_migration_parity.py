#!/usr/bin/env python3
"""Todo membro de enum Python mapeado a um tipo nativo do DB existe nas migrations.

Contexto (A40.l19 · ADR-357 §7). Dois enums acumularam 4 valores declarados só
em Python, sem nenhum ``ALTER TYPE``, e o drift ficou invisível por meses: dev e
CI rodam SQLite, onde a coluna é VARCHAR sem CHECK, então qualquer string passa.
Em Postgres o ``INSERT`` explode — e dois desses caminhos já estavam vivos.

**Por que AST e não leitura do banco.** O banco de teste nasce de
``Base.metadata.create_all``, que materializa o próprio enum Python. Compará-lo
com o Python é auto-referente: teria ficado verde durante todo o drift. As duas
metades precisam vir de fontes independentes — o enum do código e o DDL
declarado nas migrations.

**Direção: ``python ⊆ declarado``, nunca igualdade.** Postgres não tem
``DROP VALUE``; um valor removido do Python permanece no tipo para sempre, e
exigir igualdade transformaria toda remoção legítima em falha eterna.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODELS_DIR = _REPO_ROOT / "backend" / "app" / "models"
_MIGRATIONS_DIR = _REPO_ROOT / "backend" / "alembic" / "versions"

_ADD_VALUE = re.compile(
    r"ALTER\s+TYPE\s+(\w+)\s+ADD\s+VALUE\s+(?:IF\s+NOT\s+EXISTS\s+)?'([^']+)'",
    re.IGNORECASE,
)


def _enum_args_in_file(path: Path) -> set[str]:
    """Classes passadas a `Enum(X)` neste arquivo."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Enum":
            names.update(a.id for a in node.args if isinstance(a, ast.Name))
    return names


def _native_enum_class_names() -> set[str]:
    """Classes usadas como `Enum(X)` em `mapped_column` — as que viram tipo nativo no DB."""
    return set().union(*(_enum_args_in_file(p) for p in _MODELS_DIR.glob("*.py")))


def _string_constants(node: ast.ClassDef) -> set[str]:
    """Valores `x = "..."` no corpo da classe — os membros do enum."""
    return {
        stmt.value.value
        for stmt in node.body
        if isinstance(stmt, ast.Assign)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    }


def _enum_classes_in_file(path: Path, class_names: set[str]) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ClassDef) and node.name in class_names:
            found[node.name.lower()] = _string_constants(node)
    return {name: values for name, values in found.items() if values}


def _python_members(class_names: set[str]) -> dict[str, set[str]]:
    """`{tipo_no_db: {valores}}` — o tipo é a classe em lowercase (default do SQLAlchemy)."""
    found: dict[str, set[str]] = {}
    for path in _MODELS_DIR.glob("*.py"):
        found.update(_enum_classes_in_file(path, class_names))
    return found


def _enum_name_kwarg(node: ast.Call) -> str | None:
    """Valor de `name=` em `sa.Enum(..., name="x")` — o nome do tipo no Postgres."""
    for kw in node.keywords:
        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _created_types(source: str) -> dict[str, set[str]]:
    """Tipos criados por `sa.Enum("a", "b", name="t")` numa migration."""
    created: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "Enum"):
            continue
        name = _enum_name_kwarg(node)
        if name is None:
            continue
        literals = {a.value for a in node.args if isinstance(a, ast.Constant)}
        created.setdefault(name.lower(), set()).update(literals)
    return created


def _declared_in_migrations() -> dict[str, set[str]]:
    """`{tipo: {valores}}` somando criação (`sa.Enum`) e todo `ALTER TYPE ... ADD VALUE`."""
    declared: dict[str, set[str]] = {}
    for path in _MIGRATIONS_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for type_name, value in _ADD_VALUE.findall(source):
            declared.setdefault(type_name.lower(), set()).add(value)
        for type_name, values in _created_types(source).items():
            declared.setdefault(type_name, set()).update(values)
    return declared


def _drift_error(type_name: str, members: set[str], declared: dict[str, set[str]]) -> str | None:
    if type_name not in declared:
        return (
            f"{type_name}: enum Python mapeado a tipo nativo, mas nenhuma migration o cria. "
            f"Migration de criação faltando, ou o `name=` diverge do nome da classe em lowercase."
        )
    missing = members - declared[type_name]
    if not missing:
        return None
    return (
        f"{type_name}: {sorted(missing)} existe(m) no Python e não nas migrations. "
        f"Escreva `ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '<v>'` guardado por "
        f"dialeto (padrão: backend/alembic/versions/a40l19enumdrift_*.py). "
        f"SQLite não acusa; Postgres quebra no INSERT."
    )


def main() -> int:
    python_side = _python_members(_native_enum_class_names())
    declared = _declared_in_migrations()
    errors = [
        err
        for type_name, members in sorted(python_side.items())
        if (err := _drift_error(type_name, members, declared)) is not None
    ]
    if not errors:
        print(f"✓ {len(python_side)} enum(s) nativo(s) sem drift contra as migrations.")
        return 0

    print("Drift de enum Python ↔ migration (A40.l19 · ADR-357 §7):\n", file=sys.stderr)
    for err in errors:
        print(f"  ✗ {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
