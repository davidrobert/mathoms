"""Guardrail: identificadores E* legados não escapam das ilhas permitidas.

Durante a transição (Fases 1-8), alguns arquivos **precisam** mencionar nomes
legados (``STAGE_REGISTRY``, ``STAGE_RENAME_MAP``, ``_STAGE_TO_DIR``...). Este
teste garante que NOVAS menções em código não previsto viram falha de CI
antes de chegarem a produção.

**Escopo atual**: SOFT-FAIL durante Fases 1-8 — falhas são reportadas mas o
teste passa. O switch para HARD-FAIL acontece ao final da Fase 9.5 junto
com a remoção de ``LEGACY_NAMES`` como strings no código de produção.

Configuração via env var:
    ``MATHOMS_ENFORCE_STAGE_RENAME=1`` → HARD-FAIL (usado na Fase 9.5+).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO_ROOT))

from pipeline.stage_spec import STAGE_RENAME_MAP  # noqa: E402


LEGACY_NAMES = sorted(STAGE_RENAME_MAP.keys())

# Ilhas permitidas: contratos de transição, fontes de verdade e testes do map
ALLOWED_PREFIXES = (
    "pipeline/stage_spec.py",
    "pipeline/artifact_store.py",
    "pipeline/materialization_bridge.py",
    "pipeline/stage_runner_compat.py",
    "pipeline/stages/",          # wrappers que ainda usam nomes legados
    "pipeline/orchestrator.py",  # LEGACY_FROM_ALIASES
    "backend/alembic/versions/", # migrations (STAGE_RENAME, imports, comentários)
    "backend/app/scripts/",      # backfill usa strings legadas
    "backend/tests/",             # testes de migration, DBArtifactStore, etc.
    "tests/unit/pipeline/",       # testes do registry/map
    "tests/",                      # fixtures golden podem conter strings legadas
    "scripts/",                    # scripts legados E2/E3/E5
    "_scratch/",                   # scripts de auditoria
    "config/",                     # schemas JSON mencionam nomes de stage
    "docs/",                       # ADRs históricos
)


SEARCH_ROOTS = ["pipeline", "scripts", "backend", "tests", "_scratch"]


def _iter_python_files():
    for root in SEARCH_ROOTS:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for p in root_path.rglob("*.py"):
            if "__pycache__" in p.parts or ".venv" in p.parts:
                continue
            yield p


def _is_allowed(rel_path: str) -> bool:
    return any(rel_path.startswith(prefix) or rel_path == prefix for prefix in ALLOWED_PREFIXES)


def _find_occurrences() -> dict[str, list[tuple[str, int, str]]]:
    patterns = {
        name: re.compile(rf'(?<![A-Za-z0-9_\-\.]){re.escape(name)}(?![A-Za-z0-9_])')
        for name in LEGACY_NAMES
    }
    out: dict[str, list[tuple[str, int, str]]] = {}
    for p in _iter_python_files():
        rel = p.relative_to(REPO_ROOT).as_posix()
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for name, pat in patterns.items():
            for i, line in enumerate(text.splitlines(), start=1):
                if pat.search(line):
                    out.setdefault(name, []).append((rel, i, line.strip()))
    return out


@pytest.mark.parametrize("legacy_name", LEGACY_NAMES)
def test_legacy_name_only_in_allowed_files(legacy_name: str):
    hard_fail = os.environ.get("MATHOMS_ENFORCE_STAGE_RENAME", "0") == "1"
    occurrences = _find_occurrences().get(legacy_name, [])
    leaks = [
        (path, line, snippet)
        for path, line, snippet in occurrences
        if not _is_allowed(path)
    ]
    if leaks:
        msg = (
            f"Identificador legado '{legacy_name}' vazou para {len(leaks)} localização(ões):\n"
            + "\n".join(f"  {p}:{l}: {s[:100]}" for p, l, s in leaks[:10])
        )
        if hard_fail:
            pytest.fail(msg)
        # Soft-fail durante Fases 1-8: só printa.
        print(msg)
