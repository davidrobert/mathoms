#!/usr/bin/env python3
"""Garante que ``pipeline/**`` não instancia `Session` SQLAlchemy própria — stages reusam ``ctx.get_artifact_store().session`` ou recebem ``db: Session`` por parâmetro kwarg-only (ADR-256; uso: ``python dev/check_pipeline_sessions.py [-v]``; exit 1 = violação)."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Símbolos cuja construção/import em pipeline/** indica session paralela.
# `Session` está fora porque é tipo abstrato usado em type hints (`db: Session`)
# — call-sites legítimos passam, não constroem.
FORBIDDEN_NAMES = frozenset(
    {
        "SyncSessionLocal",
        "AsyncSessionLocal",
        "async_session",
        "sessionmaker",
        "scoped_session",
        "async_sessionmaker",
        "async_scoped_session",
    }
)

# Módulo backend que expõe as factories proibidas.
FORBIDDEN_MODULES = frozenset({"backend.app.core.database"})

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_ROOT = _REPO_ROOT / "pipeline"


def _from_import_violation(node: ast.ImportFrom, path: Path) -> list[str]:
    if node.module not in FORBIDDEN_MODULES:
        return []
    return [
        f"{path}:{node.lineno}: forbidden import `{node.module}.{alias.name}` "
        "(see ADR-256: stages do not open own Session)"
        for alias in node.names
        if alias.name in FORBIDDEN_NAMES
    ]


def _import_violation(node: ast.Import, path: Path) -> list[str]:
    return [
        f"{path}:{node.lineno}: forbidden import `{alias.name}` "
        "(see ADR-256: stages do not open own Session)"
        for alias in node.names
        if alias.name in FORBIDDEN_MODULES
    ]


def _node_import_violations(node: ast.AST, path: Path) -> list[str]:
    if isinstance(node, ast.ImportFrom):
        return _from_import_violation(node, path)
    if isinstance(node, ast.Import):
        return _import_violation(node, path)
    return []


def _check_imports(tree: ast.Module, path: Path) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        out.extend(_node_import_violations(node, path))
    return out


def _check_calls(tree: ast.Module, path: Path) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _callee_name(node.func)
        if name and name in FORBIDDEN_NAMES:
            out.append(
                f"{path}:{node.lineno}: forbidden call `{name}(...)` "
                f"(see ADR-256: reuse ctx.get_artifact_store().session or accept db: Session)"
            )
    return out


def _callee_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _violations_in_file(path: Path) -> list[str]:
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [f"{path}: parse error: {exc}"]
    return _check_imports(tree, path) + _check_calls(tree, path)


def collect_violations() -> list[str]:
    errors: list[str] = []
    if not _PIPELINE_ROOT.is_dir():
        return [f"pipeline/ not found at {_PIPELINE_ROOT}"]
    for path in sorted(_PIPELINE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        errors.extend(_violations_in_file(path))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    errors = collect_violations()
    if args.verbose and not errors:
        print(f"OK: no parallel Session under {_PIPELINE_ROOT} (ADR-256)", file=sys.stderr)
    for line in errors:
        print(line, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
