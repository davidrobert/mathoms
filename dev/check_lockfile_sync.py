#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-commit hook: requirements.lock em sincronia com os *.in (ADR-254)."""

# Falha se um pacote direto declarado em requirements.in/backend/requirements.in
# está ausente do lock combinado requirements.lock. NÃO regenera o lock — isso
# exige container linux/amd64 (runbook docs/reference/runbooks/python_dependencies.md);
# só detecta drift. Roda com pass_filenames: false (conjunto fixo).

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_FILES = (REPO_ROOT / "requirements.in", REPO_ROOT / "backend" / "requirements.in")
LOCK_FILE = REPO_ROOT / "requirements.lock"

_NORMALIZE = re.compile(r"[-_.]+")  # PEP 503: lowercase, [-_.]+ → "-"
_IN_DEP = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
_LOCK_DEP = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==")


def _normalize(name: str) -> str:
    return _NORMALIZE.sub("-", name).lower()


def _names(path: Path, pattern: re.Pattern[str]) -> set[str]:
    names: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        m = pattern.match(line)
        if m:
            names.add(_normalize(m.group(1)))
    return names


def _declared() -> set[str] | None:
    declared: set[str] = set()
    for in_file in IN_FILES:
        if not in_file.exists():
            print(f"[lockfile-sync] esperado {in_file} não encontrado.")
            return None
        declared |= _names(in_file, _IN_DEP)
    return declared


def main() -> int:
    if not LOCK_FILE.exists():
        print(f"[lockfile-sync] {LOCK_FILE.name} não existe — gere via runbook.")
        return 1
    declared = _declared()
    if declared is None:
        return 1
    missing = sorted(declared - _names(LOCK_FILE, _LOCK_DEP))
    if missing:
        print(
            "[lockfile-sync] deps em *.in ausentes de requirements.lock: "
            f"{', '.join(missing)} → regenere o lock "
            "(docs/reference/runbooks/python_dependencies.md Tarefa 1)."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
