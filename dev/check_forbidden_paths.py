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
"""

from __future__ import annotations

import sys

# Alinhado com dev/commit.py — mudar lá mudar aqui.
FORBIDDEN_DIRS = (
    "storage/",
    "data/",
    "inbox/",
    "inbox_processed/",
    "_scratch/",
)

FORBIDDEN_FILES = (
    ".env",
    ".env.test",
    "fin.db",
    "config/passwords.txt",
)

FORBIDDEN_SUFFIXES = (
    ".db",
    ".sqlite",
    ".sqlite3",
)


def check(path: str) -> str | None:
    """Retorna a razão da violação, ou None se passou."""
    for forbidden in FORBIDDEN_DIRS:
        if path.startswith(forbidden):
            return f"diretório proibido: {forbidden}"
    if path in FORBIDDEN_FILES:
        return f"arquivo proibido: {path}"
    for suffix in FORBIDDEN_SUFFIXES:
        if path.endswith(suffix):
            return f"sufixo proibido: {suffix}"
    return None


def main() -> int:
    violations: list[tuple[str, str]] = []
    for path in sys.argv[1:]:
        reason = check(path)
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
