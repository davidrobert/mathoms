#!/usr/bin/env python3
"""Todo engine SQLAlchemy fora de teste nasce com ``hide_parameters=True``.

Uso: ``python3 dev/check_engine_hide_parameters.py [-v]``; exit 1 = violação.

`str(StatementError)` traz ``[parameters: ...]``, os bound parameters do statement.
Medido em 2026-10-08 (PG 16): o `DataError` de `match_or_create` levou endereço e
nome do imóvel ao `stage_log`, ao canal do WS e ao traceback. O flag corta na fonte,
para todo sink — log, span, result backend do Celery e o console de script de
operador, que roda dentro de sessão de agente e vira transcript.

AST, não regex, e o kwarg tem de ser o literal ``True``: ``**opts`` sem ele reprova,
porque o valor efetivo deixa de ser decidível. Full-scan dos ``.py`` versionados — o
ofensor entra como arquivo novo, não como edição de um existente. O texto do
call-site é metade da trava; a outra é comportamental, sobre o objeto que produção
constrói: `backend/tests/test_engines_de_producao_nao_ecoam_bound_parameters.py`.

Fora do scan: todo diretório ``tests`` (``tests/``, ``backend/tests/``,
``pipeline-service/tests/``). Fixture de teste cria engine SEM o flag de propósito,
para provar a redação nas fronteiras que não dependem dele.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ENGINE_FACTORIES = frozenset(
    {"create_engine", "create_async_engine", "engine_from_config", "async_engine_from_config"}
)
_REPO_ROOT = Path(__file__).resolve().parents[1]

# Construtores de produção que o scan TEM de enxergar. Zero aqui é leitura vazia
# (forma de chamada que o detector não conhece), não repo limpo.
_ANCHORS = ("backend/app/core/database.py", "backend/alembic/env.py")

_REMEDY = (
    "sem `hide_parameters=True` literal — `str(StatementError)` ecoa os bound "
    "parameters (PII) em log, stage_log, WS e traceback"
)


def _factory_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _hides_parameters(call: ast.Call) -> bool:
    return any(
        kw.arg == "hide_parameters"
        and isinstance(kw.value, ast.Constant)
        and kw.value.value is True
        for kw in call.keywords
    )


def engine_constructors(tree: ast.AST) -> list[ast.Call]:
    """Chamadas a factory de engine, em qualquer forma (`f(...)`, `sa.f(...)`, aninhada)."""
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _factory_name(n) in ENGINE_FACTORIES
    ]


def violations_in_source(src: str, path: str) -> tuple[list[str], int]:
    """(violações, construtores vistos). Parse quebrado é violação, nunca pulo."""
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as exc:
        return [f"{path}: parse error: {exc}"], 0
    calls = engine_constructors(tree)
    violations = [
        f"{path}:{c.lineno}: `{_factory_name(c)}(...)` {_REMEDY}"
        for c in calls
        if not _hides_parameters(c)
    ]
    return violations, len(calls)


def _is_test_path(rel: str) -> bool:
    return "tests" in Path(rel).parts[:-1]


def _tracked_python_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"],
        cwd=_REPO_ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode()
    return sorted(p for p in out.split("\0") if p and not _is_test_path(p))


def _anchor_violations(seen: dict[str, int]) -> list[str]:
    return [
        f"{a}: nenhum construtor de engine visto — leitura vazia; o detector "
        "precisa conhecer a forma nova de construir o engine"
        for a in _ANCHORS
        if not seen.get(a)
    ]


def collect_violations() -> tuple[list[str], int]:
    violations: list[str] = []
    seen: dict[str, int] = {}
    for rel in _tracked_python_files():
        path = _REPO_ROOT / rel
        if not path.is_file():
            continue
        found, count = violations_in_source(path.read_text(encoding="utf-8"), rel)
        violations.extend(found)
        seen[rel] = count
    return violations + _anchor_violations(seen), sum(seen.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    violations, total = collect_violations()
    for v in violations:
        print(v, file=sys.stderr)
    if violations:
        print(f"check_engine_hide_parameters: {len(violations)} violação(ões)", file=sys.stderr)
        return 1
    if args.verbose:
        print(f"check_engine_hide_parameters: {total} construtor(es), todos com o flag")
    return 0


if __name__ == "__main__":
    sys.exit(main())
