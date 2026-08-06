#!/usr/bin/env python3
"""Garante que `backend/` só importa de `tests.`/`scripts.` (raiz, não `backend.tests`) via `_ALLOWED_CROSS_BOUNDARY_PREFIXES` (ADR-210 §Adendo 2026-08-05): o filtro `pipeline_lib` de `ci.yml` gateia `backend-tests` por um allowlist estreito — import novo fora dele fica invisível ao CI (allowlist positiva falha ABERTA), então este gate falha fechado no PR que introduz o import, forçando o filtro a crescer junto.

Uso:
    python3 dev/check_backend_pipeline_coupling.py
    python3 dev/check_backend_pipeline_coupling.py --verbose

Exit 0 = OK, 1 = import cross-boundary fora do allowlist OU entrada do
allowlist não-exercida (dead scope — o filtro ficou mais largo que o uso real).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Iterator

# Espelha os paths de `tests/`/`scripts/` no grupo `pipeline_lib` de
# `.github/workflows/ci.yml` — se um import novo cruzar a fronteira sem
# entrar aqui, `backend-tests` não dispara na mudança que o quebra.
_ALLOWED_CROSS_BOUNDARY_PREFIXES: dict[str, str] = {
    "tests.fakes": "cobertura por tests/fakes/** no filtro pipeline_lib",
    "scripts.route_documents": "cobertura por scripts/route_documents.py no filtro pipeline_lib",
    "scripts.pipeline_common": "cobertura por scripts/pipeline_common.py no filtro pipeline_lib — módulo compartilhado (CLAUDE.md), importado por DBArtifactStore/artifact_retention em produção",
    "scripts.e2": "cobertura por scripts/e2/** no filtro pipeline_lib — parsers de banco (registry + banks/<banco>.py)",
    "scripts.reconcile_transactions": "cobertura por scripts/reconcile_transactions.py no filtro pipeline_lib — o predicado da sombra do colapso (ADR-364) só é alcançável com DBArtifactStore real, logo o teste dele mora em backend/tests/",
}
_BOUNDARY_ROOTS = frozenset({"tests", "scripts"})

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_ROOT = _REPO_ROOT / "backend"


def _module_names(node: ast.AST) -> Iterator[tuple[str, int]]:
    """`from tests import fakes` reconstrói para `tests.fakes` — sem isso o
    prefixo do alias se perde e o allowlist compara contra o pacote errado.
    Guard clauses (não `if`/`elif`) de propósito: `elif` é `If` aninhado no
    `orelse` do AST, e o `for` dentro dele mediria profundidade 3."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name, node.lineno
        return
    if not (isinstance(node, ast.ImportFrom) and node.module and node.level == 0):
        return
    for alias in node.names:
        yield f"{node.module}.{alias.name}", node.lineno


def _imported_modules(tree: ast.AST) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        yield from _module_names(node)


def _is_boundary_crossing(module: str) -> bool:
    root = module.split(".", 1)[0]
    return root in _BOUNDARY_ROOTS


def _exercised_prefix(module: str) -> str | None:
    for prefix in _ALLOWED_CROSS_BOUNDARY_PREFIXES:
        if module == prefix or module.startswith(f"{prefix}."):
            return prefix
    return None


def _classify_import(path: Path, module: str, lineno: int) -> tuple[str | None, str | None]:
    """(prefixo_exercido, violação) — no máx. um dos dois é não-`None`."""
    if not _is_boundary_crossing(module):
        return None, None
    prefix = _exercised_prefix(module)
    if prefix is not None:
        return prefix, None
    violation = (
        f"{path}:{lineno}: import `{module}` cruza para tests./scripts. "
        "fora do allowlist — adicione o path a _ALLOWED_CROSS_BOUNDARY_PREFIXES "
        "(dev/check_backend_pipeline_coupling.py) E ao filtro pipeline_lib "
        "(.github/workflows/ci.yml)"
    )
    return None, violation


def scan_file(path: Path) -> tuple[list[str], set[str]]:
    """Retorna (violações, prefixos-exercidos) para um arquivo."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as e:
        return [f"{path}: parse error: {e}"], set()

    violations: list[str] = []
    exercised: set[str] = set()
    for module, lineno in _imported_modules(tree):
        prefix, violation = _classify_import(path, module, lineno)
        if prefix:
            exercised.add(prefix)
        if violation:
            violations.append(violation)
    return violations, exercised


def scan_all(backend_root: Path = _BACKEND_ROOT) -> tuple[list[str], set[str]]:
    violations: list[str] = []
    exercised: set[str] = set()
    for path in sorted(backend_root.rglob("*.py")):
        file_violations, file_exercised = scan_file(path)
        violations.extend(file_violations)
        exercised |= file_exercised
    return violations, exercised


def _unexercised_entries(exercised: set[str]) -> list[str]:
    return [prefix for prefix in _ALLOWED_CROSS_BOUNDARY_PREFIXES if prefix not in exercised]


def _unexercised_message(prefix: str) -> str:
    return (
        f"✗ allowlist não-exercido: `{prefix}` não é importado por nenhum "
        "arquivo em backend/ — remova a entrada (aqui e do filtro pipeline_lib)."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    violations, exercised = scan_all()
    unexercised = _unexercised_entries(exercised)
    if not violations and not unexercised:
        if args.verbose:
            print(f"✓ {len(exercised)} entrada(s) do allowlist exercidas, 0 violação.")
        return 0

    for v in violations:
        print(f"✗ {v}")
    for prefix in unexercised:
        print(_unexercised_message(prefix))
    return 1


if __name__ == "__main__":
    sys.exit(main())
