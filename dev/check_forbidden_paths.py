#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev/check_forbidden_paths.py — hook para pre-commit.

Recebe paths via argv (comportamento padrão do pre-commit) e falha (exit 1)
se qualquer um estiver em diretório proibido, for arquivo proibido por nome
ou tiver sufixo proibido.

Mantém em sincronia com `dev/commit.py`: a intenção é que pre-commit rode
esta mesma validação em CI, git hooks locais e via dev/commit.py — defense
in depth.

Nota: `storage/` cobre uploads multi-tenant; `data/`/`inbox/` cobrem o pipeline
CLI na raiz do repo — ver `dev/README.md`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Alinhado com dev/commit.py — mudar lá mudar aqui.
FORBIDDEN_DIRS = (
    "storage/",
    "data/",
    "inbox/",
    "inbox_processed/",
    "_scratch/",
)

FORBIDDEN_FILES = (
    "mathoms.db",
    "config/passwords.txt",
    # F7F-Local (ADR-116): credenciais de operadores internos nunca vão
    # para o git. Apenas `config/internal_operators.example.yaml` é commitável.
    "config/internal_operators.yaml",
)

# Basenames bloqueados em qualquer diretório (regressão: backend/.env vazou
# porque o match era exato; .env no root era pego, subdirs passavam).
FORBIDDEN_BASENAMES = (
    ".env",
    ".env.test",
)

FORBIDDEN_SUFFIXES = (
    ".db",
    ".sqlite",
    ".sqlite3",
)


def _staged_deletion_paths(repo_root: Path) -> set[str]:
    """Paths com delete staged (`git diff --cached`) — remover `.env` do repo é OK."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--cached", "--name-status"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0 or not proc.stdout:
        return set()
    out: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status == "D":
            out.add(parts[1])
    return out


def check(path: str, *, staged_deletions: set[str] | None = None) -> str | None:
    """Retorna a razão da violação, ou None se passou."""
    for forbidden in FORBIDDEN_DIRS:
        if path.startswith(forbidden):
            return f"diretório proibido: {forbidden}"
    basename = path.rsplit("/", 1)[-1]
    if basename in FORBIDDEN_BASENAMES:
        if staged_deletions is not None and path in staged_deletions:
            return None
        return f"arquivo proibido: {basename} (em {path})"
    if path in FORBIDDEN_FILES:
        if staged_deletions is not None and path in staged_deletions:
            return None
        return f"arquivo proibido: {path}"
    for suffix in FORBIDDEN_SUFFIXES:
        if path.endswith(suffix):
            return f"sufixo proibido: {suffix}"
    return None


def main() -> int:
    repo_root = Path.cwd()
    staged_del = _staged_deletion_paths(repo_root)
    violations: list[tuple[str, str]] = []
    for path in sys.argv[1:]:
        reason = check(path, staged_deletions=staged_del)
        if reason:
            violations.append((path, reason))

    if not violations:
        return 0

    print("✗ pre-commit: paths proibidos detectados:", file=sys.stderr)
    for path, reason in violations:
        print(f"    {path} — {reason}", file=sys.stderr)
    print(
        "\nEsses paths nunca devem ir pro git. Se caíram aqui por engano:\n"
        "  - verifique o .gitignore\n"
        "  - remova do staging: git restore --staged <path>\n"
        "  - em último caso, contorne com --no-verify (NÃO recomendado)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
