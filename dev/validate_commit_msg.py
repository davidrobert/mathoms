#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev/validate_commit_msg.py — hook commit-msg para pre-commit.

Lê o arquivo de mensagem passado como único argumento e falha (exit 1) se
a primeira linha não seguir o padrão de prefixo aceito no repo.

Alinhado com dev/commit.py::VALID_PREFIXES — manter em sincronia.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VALID_PREFIXES = (
    # Produto web (atual)
    "feat:", "fix:", "refactor:", "perf:", "style:", "test:", "chore:",
    "backend:", "frontend:", "api:", "db:", "infra:", "ci:",
    "docs:", "update:",
    # Pipeline / CLI legacy
    "pipeline:", "config:",
    "pre-update:", "pre-reset:", "E-reset:", "E-reset-from-",
    "E1:", "E2:", "E3:", "E4:", "E5:", "E5.N:", "E6:", "E6-regen:", "E7:",
    "init:",
)

_PREFIX_WITH_SCOPE = re.compile(
    r"^(feat|fix|refactor|perf|style|test|chore|backend|frontend|api|db|infra|ci|docs|update|pipeline|config)\([^)]+\):"
)


def main() -> int:
    if len(sys.argv) < 2:
        print("✗ commit-msg: arquivo de mensagem não fornecido", file=sys.stderr)
        return 1

    msg_file = Path(sys.argv[1])
    first_line = msg_file.read_text(encoding="utf-8", errors="replace").splitlines()[0].strip() if msg_file.exists() else ""

    if not first_line or first_line.startswith("#"):
        # Mensagem vazia — git já cancela sozinho.
        return 0

    # Merge commits e revert commits são OK
    if first_line.startswith(("Merge ", "Revert ")):
        return 0

    if _PREFIX_WITH_SCOPE.match(first_line):
        return 0

    if any(first_line.startswith(p) for p in VALID_PREFIXES):
        return 0

    print("✗ commit-msg: prefixo inválido", file=sys.stderr)
    print(f"    mensagem: {first_line}", file=sys.stderr)
    print(f"    aceitos: {', '.join(VALID_PREFIXES[:10])}…", file=sys.stderr)
    print("    exemplos: 'feat: …', 'fix(api): …', 'docs: …'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
