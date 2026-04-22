"""AST-lite enforcement: sem filenames genéricos (CLAUDE.md §Code style · A6g.6).

Complementa ``dev/check_forbidden_names.py`` (pre-commit) — este teste
roda no CI como fail-safe e cobre varredura do repo inteiro, não só
arquivos staged.

Regra: nenhum arquivo com nome ``utils.py/ts(x)``, ``helpers.py/ts(x)``,
``manager.py/ts(x)``, ``handler.py/ts(x)``, ``service.py/ts``. Match
exato (não prefixo) — ``audit_helpers.py`` é OK. Classes proibidas
(``Manager``, ``Service`` sozinho, ``Utils``, ``Helpers``) cobertas
pelo audit geral (P6); aqui focamos em filenames.

ALLOWLIST cobre exceções históricas com track.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND = ROOT / "backend" / "app"
PIPELINE = ROOT / "pipeline"
SCRIPTS = ROOT / "scripts"
FRONTEND_SRC = ROOT / "frontend" / "src"

FORBIDDEN = {
    "utils.py",
    "helpers.py",
    "manager.py",
    "handler.py",
    "utils.ts",
    "helpers.ts",
    "manager.ts",
    "handler.ts",
    "utils.tsx",
    "helpers.tsx",
    "manager.tsx",
    "handler.tsx",
    "service.py",
    "service.ts",
}

ALLOWLIST = {
    # Legado (A6g.6 baseline 2026-04-22). Renomear em A6g.2c.
    "pipeline/llm/service.py",
}

SEARCH_DIRS = [BACKEND, PIPELINE, SCRIPTS, FRONTEND_SRC]


def _iter_candidate_files():
    for root in SEARCH_DIRS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.name not in FORBIDDEN:
                continue
            rel = p.relative_to(ROOT).as_posix()
            # Pula node_modules, generated/, venv, cache
            if any(s in rel for s in ("node_modules", "generated/", ".venv", "__pycache__")):
                continue
            yield rel


def test_no_new_forbidden_filenames() -> None:
    """Nenhum arquivo com nome genérico fora da allowlist."""
    offenders = [rel for rel in _iter_candidate_files() if rel not in ALLOWLIST]
    assert not offenders, (
        "Filename(s) genérico(s) detectado(s) (CLAUDE.md §Code style):\n"
        + "\n".join(f"  {o}" for o in offenders)
        + "\n\nRegra: use nomes específicos (<5 hits em grep -r). "
        "Ex: `bank_parser.py` não `utils.py`; `EmergencyReserveCalculator.py` "
        "não `ReserveHelper.py`. Para helpers de aggregate, prefixe: "
        "`format_helpers.py`, `audit_helpers.py`, `_helpers.py`."
    )


def test_allowlist_entries_exist() -> None:
    """Allowlist consistente: nenhuma entrada órfã."""
    missing = [rel for rel in ALLOWLIST if not (ROOT / rel).exists()]
    assert not missing, (
        f"ALLOWLIST tem entradas órfãs — arquivo renomeado/deletado. "
        f"Remova de ALLOWLIST: {missing}"
    )
