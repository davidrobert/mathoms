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
SCAN_ROOTS = (REPO / "pipeline", REPO / "scripts", REPO / "backend")
ALLOWLIST: dict[tuple[str, str], str] = {
    ("scripts/analyze_finances.py", "_load_caixa_from_e3_saldos"): "legacy-disk",
    ("pipeline/domain/services/wise_fiscal_flags.py", "_soma_non_usd_em_usd"): "cbe-cross-usd",
}
# O `_?` não é cosmético: a lista nasceu do *parâmetro* de ``__init__``
# (``cambio_usd_brl``) enquanto a instância guarda ``self._cambio_usd_brl`` — o
# atributo que um produtor novo de fato multiplicaria era o único invisível
# (A40.l63 §Ataque, medido 3/10).
_RATE_NAME = re.compile(r"^_?(cambio|ptax)\w*$|^(usd|eur|gbp)_brl$", re.I)
_RATE_ATTR = frozenset(
    {
        "rate",
        "taxa",
        "cambio_usd",
        "cambio_eur",
        "cambio_usd_brl",
        "cambio_eur_brl",
        "_cambio_usd_brl",
        "_cambio_eur_brl",
    }
)
_RATE_KEY = re.compile(r"^(cambio|ptax)", re.I)


def _is_rate_expr(node: ast.AST) -> bool:
    """Reconhece a taxa mesmo embrulhada em call/subscript/cast."""
    if isinstance(node, ast.Name):
        return bool(_RATE_NAME.match(node.id))
    if isinstance(node, ast.Attribute):
        return node.attr in _RATE_ATTR or bool(_RATE_NAME.match(node.attr))
    if isinstance(node, ast.Subscript):
        return _is_rate_key(node.slice)
    if isinstance(node, ast.Call):
        # `safe_float(self._taxas.get("cambio_usd_brl", 5.80))` — a taxa é
        # nomeada pela *chave*, não por um Name; sem isto a linha pré-390
        # reentra apenas trocando o local por uma resolução inline.
        return any(_is_rate_expr(a) or _is_rate_key(a) for a in node.args) or _is_rate_expr(
            node.func
        )
    return False


def _is_rate_key(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(_RATE_KEY.match(node.value))
    )


def _enclosing_function(stack: list[ast.AST]) -> str:
    for node in reversed(stack):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return "<module>"


def _multiplies_by_rate(node: ast.AST) -> bool:
    """`x * cambio` e `x *= cambio` — a segunda forma escapava por não ser BinOp,
    e `+=`/`*=` é o idioma dominante da própria função que este gate protege."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _is_rate_expr(node.left) or _is_rate_expr(node.right)
    if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Mult):
        return _is_rate_expr(node.value)
    return False


def _scan_file(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[tuple[int, str]] = []
    stack: list[ast.AST] = []

    class Visitor(ast.NodeVisitor):
        def generic_visit(self, node: ast.AST) -> None:
            stack.append(node)
            if _multiplies_by_rate(node):
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
        if rel_s == str(SINK):
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
