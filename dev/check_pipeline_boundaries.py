#!/usr/bin/env python3
"""Garante que ``pipeline/`` não importa frameworks de servidor/ORM nem ``backend``.

Regra (P1): ``fastapi``, ``celery``, ``sqlalchemy`` e ``backend`` não podem
aparecer em imports em ``pipeline/**/*.py`` — mantém a dependência unidirecional
api/tasks → pipeline → scripts (ADR-089 tightening; ADR-325).

Exceção declarativa: ``_BACKEND_ALLOWLIST`` lista arquivos do composition root do
pipeline que legitimamente importam ``backend`` (injeção de session/eventos), com
motivo. NÃO é escape hatch: (a) só exime o root ``backend`` — frameworks seguem
proibidos até nesses arquivos; (b) entrada não-exercida (arquivo sem import de
``backend``) FALHA o gate, forçando o allowlist a só encolher.

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
from typing import Iterator

FORBIDDEN_ROOTS = frozenset({"fastapi", "celery", "sqlalchemy", "backend"})

# Arquivos (path relativo a ``pipeline/``) que podem importar ``backend``, com
# motivo declarado. ``TODO A36.l1-B`` = temporário; a inversão via port injetada
# no ``WorkspaceContext`` (ADR-325 §Parte B) remove o import e a entrada.
_BACKEND_ALLOWLIST: dict[str, str] = {
    "cli_run_stage.py": "composition root — injeta session/otel/hydrated context no boundary",
    "live_progress.py": "bridge de eventos (composition root) — publish_stage_activity/item_progress",
    "stages/extract_comprovantes_bens.py": "TODO A36.l1-B: inverter vehicle_upsert + apolice via port",
    "stages/parecer_planejador.py": "TODO A36.l1-B: inverter parecer_orchestrator via port (família llm_*)",
}

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_ROOT = _REPO_ROOT / "pipeline"


def _imported_modules(tree: ast.AST) -> Iterator[tuple[str, int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno, f"import `{alias.name}`"
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module, node.lineno, f"from-import `{node.module}`"


def _scan_file(path: Path, *, backend_allowed: bool) -> tuple[list[str], bool]:
    """Retorna (violações, exerceu_allowlist). ``backend_allowed`` pula o root
    ``backend`` (não os frameworks)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as e:
        return [f"{path}: parse error: {e}"], False
    out: list[str] = []
    exercised = False
    for module, lineno, label in _imported_modules(tree):
        root = module.split(".", 1)[0]
        if root not in FORBIDDEN_ROOTS:
            continue
        if root == "backend" and backend_allowed:
            exercised = True
            continue
        out.append(f"{path}:{lineno}: forbidden {label}")
    return out, exercised


def collect_violations() -> list[str]:
    if not _PIPELINE_ROOT.is_dir():
        return [f"pipeline/ not found at {_PIPELINE_ROOT}"]
    errors: list[str] = []
    exercised: set[str] = set()
    for path in sorted(_PIPELINE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(_PIPELINE_ROOT).as_posix()
        file_errors, used = _scan_file(path, backend_allowed=rel in _BACKEND_ALLOWLIST)
        errors.extend(file_errors)
        if used:
            exercised.add(rel)
    for rel in sorted(_BACKEND_ALLOWLIST):
        if rel not in exercised:
            errors.append(
                f"stale allowlist entry (sem import de `backend`): {rel} — remova de _BACKEND_ALLOWLIST"
            )
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
