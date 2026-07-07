"""Structural AST test — guarda que nenhum script deterministico do pipeline
invoca ``_init_config`` no top-level do módulo (Sessão A6d.1).

Padrão A3b: globals começam com defaults sensatos no nível de módulo;
``_init_config(base_dir)`` é invocado apenas por ``main(root_dir=...)`` e
``main_with_store(ctx)``. Side-effects de import quebram ambientes sem
``config/`` completo (CI mínimo, helpers usados em isolamento).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

SCRIPTS_TO_CHECK = [
    "scripts/reconcile_transactions.py",
    "scripts/categorize_transactions.py",
    "scripts/analyze_finances.py",
    "scripts/e5n_narrativas.py",
    "scripts/e7_review.py",
    "scripts/consolidate_baseline.py",
]


def _toplevel_init_config_calls(tree: ast.Module) -> list[int]:
    """Retorna linhas de ``_init_config(...)`` em escopo top-level (Module body).

    Ignora chamadas dentro de ``def`` / ``async def`` (definições de função).
    Trata como top-level qualquer nó *executado* na carga do módulo —
    incluindo blocos ``if``, ``try``, ``with`` no Module body — porque eles
    rodam no momento do import.
    """
    offending: list[int] = []

    def visit(node: ast.AST, in_function: bool) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in node.body:
                visit(child, in_function=True)
            return
        if (
            not in_function
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_init_config"
        ):
            offending.append(node.lineno)
        for child in ast.iter_child_nodes(node):
            visit(child, in_function=in_function)

    for node in tree.body:
        visit(node, in_function=False)
    return offending


@pytest.mark.parametrize("relpath", SCRIPTS_TO_CHECK)
def test_no_init_config_at_import(relpath: str) -> None:
    path = _REPO_ROOT / relpath
    assert path.exists(), f"script não encontrado: {path}"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offending = _toplevel_init_config_calls(tree)
    assert not offending, (
        f"{relpath} invoca _init_config no top-level (linhas {offending}). "
        "Padrão A3b/A6d.1: side-effect proibido no import — chamar apenas "
        "dentro de main(root_dir=...) / main_with_store(ctx)."
    )
