#!/usr/bin/env python3
"""Gate ADR-390 D4: multiplicação por câmbio/PTAX só em conversao_me.py.

O funil estrutural é o tipo. Este ratchet fecha a sintaxe: `x * cambio*` /
`x * quote.rate` / `x * ptax*` fora do conversor é ofensor, salvo allowlist
nominal `(path, função) → WHY`.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SINK = Path("pipeline/domain/services/conversao_me.py")
SCAN_ROOTS = (REPO / "pipeline", REPO / "scripts")
ALLOWLIST: dict[tuple[str, str], str] = {
    ("scripts/analyze_finances.py", "_load_caixa_from_e3_saldos"): "legacy-disk",
    ("pipeline/domain/services/wise_fiscal_flags.py", "_soma_non_usd_em_usd"): "cbe-cross-usd",
}
_RATE_NAME = re.compile(r"^(cambio|ptax)", re.I)
_RATE_ATTR = frozenset({"rate", "cambio_usd", "cambio_eur", "cambio_usd_brl", "cambio_eur_brl"})


def _is_rate_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and _RATE_NAME.match(node.id):
        return True
    if isinstance(node, ast.Attribute):
        return node.attr in _RATE_ATTR or bool(_RATE_NAME.match(node.attr))
    return False


def _enclosing_function(stack: list[ast.AST]) -> str:
    for node in reversed(stack):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return "<module>"


def _scan_file(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[tuple[int, str]] = []
    stack: list[ast.AST] = []

    class Visitor(ast.NodeVisitor):
        def generic_visit(self, node: ast.AST) -> None:
            stack.append(node)
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                if _is_rate_expr(node.left) or _is_rate_expr(node.right):
                    hits.append((node.lineno, _enclosing_function(stack)))
            super().generic_visit(node)
            stack.pop()

    Visitor().visit(tree)
    return hits


def iter_py(roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        files.extend(p for p in root.rglob("*.py") if p.is_file())
    return sorted(files)


def offenders(roots: tuple[Path, ...] = SCAN_ROOTS) -> list[str]:
    bad: list[str] = []
    for path in iter_py(roots):
        rel = path.relative_to(REPO) if path.is_relative_to(REPO) else path
        rel_s = str(rel)
        if path.name == SINK.name:
            continue
        for lineno, fn in _scan_file(path):
            why = ALLOWLIST.get((rel_s, fn))
            if why:
                continue
            bad.append(f"{rel_s}:{lineno} {fn}")
    return bad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, action="append")
    args = parser.parse_args(argv)
    roots = tuple(args.root) if args.root else SCAN_ROOTS
    bad = offenders(roots)
    if not bad:
        return 0
    print("multiplicação ME→BRL fora de conversao_me.py (ADR-390 D4):", file=sys.stderr)
    for item in bad:
        print(f"  {item}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
