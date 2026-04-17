#!/usr/bin/env python3
"""Garante que ``pipeline/`` não importa frameworks de servidor ou ORM.

Regra (P1): ``fastapi``, ``celery``, ``sqlalchemy`` não podem aparecer em imports
em ``pipeline/**/*.py`` — mantém dependência unidirecional api/tasks → pipeline → scripts.

Uso:
    python dev/check_pipeline_boundaries.py
    python dev/check_pipeline_boundaries.py --verbose

Exit 0 = OK, 1 = violação encontrada.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

FORBIDDEN_ROOTS = frozenset({"fastapi", "celery", "sqlalchemy"})

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_ROOT = _REPO_ROOT / "pipeline"


def _violations_in_file(path: Path) -> list[str]:
    out: list[str] = []
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (OSError, SyntaxError) as e:
        return [f"{path}: parse error: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_ROOTS:
                    out.append(f"{path}:{node.lineno}: forbidden import `{alias.name}`")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in FORBIDDEN_ROOTS:
                out.append(f"{path}:{node.lineno}: forbidden from-import `{node.module}`")
    return out


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
        print(f"OK: no forbidden imports under {_PIPELINE_ROOT}", file=sys.stderr)
    for line in errors:
        print(line, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
