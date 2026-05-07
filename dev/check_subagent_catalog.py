#!/usr/bin/env python3
"""Gate pre-commit: CLAUDE.md tem catálogo de subagentes sincronizado (W6-T04)."""

# Wrapper sobre `dev/build_subagent_catalog.py --check` — entry-point separado
# para deixar pre-commit/CI explícitos (`check_*.py` valida; `build_*.py` gera).
# Falha se CLAUDE.md não tem as marcações ou se o bloco difere do gerado a
# partir de `.claude/agents/*.md`. Fix: rode
# `python3 dev/build_subagent_catalog.py --inline` e commite o diff.

from __future__ import annotations

import sys

from build_subagent_catalog import main as build_main


def main() -> int:
    sys.argv = ["check_subagent_catalog", "--check"]
    return build_main()


if __name__ == "__main__":
    sys.exit(main())
