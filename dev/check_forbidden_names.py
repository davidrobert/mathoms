#!/usr/bin/env python3
"""A6g.6 slice 3 · ADR-114 — bloqueia filenames genéricos (CLAUDE.md §Code style).

Filenames proibidos (match exato, não sufixo):
    utils.py, helpers.py, manager.py, handler.py,
    utils.ts, helpers.ts, manager.ts, handler.ts,
    utils.tsx, helpers.tsx, manager.tsx, handler.tsx,
    service.py / service.ts (quando sozinho, sem prefixo)

Prefixos ADR-089 são aceitos — `audit_helpers.py`, `format_helpers.py`,
`_helpers.py` (privado de aggregate), `bank_parser.py`. Arquivos com
escopo explícito no nome (`EmergencyReserveCalculator.py`) também OK.

Allowlist: exceções históricas citadas por track. `pipeline_common.py` é
o exemplo canônico — mora em scripts/ e consolida paths + config I/O
(ADR histórica).

Exit 0 se todos os staged passam; exit 1 com listagem dos ofensores
caso contrário. Chamado via pre-commit com `pass_filenames: true`.
"""
from __future__ import annotations

import sys
from pathlib import Path

FORBIDDEN_FILENAMES = {
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

# Exceções históricas (com track documentado). Nunca adicionar novas entradas
# sem ADR/track explícito — prefira renomear.
ALLOWLIST = {
    # Legado pipeline (A6g.6 baseline 2026-04-22). Renomear em A6g.2c.
    "pipeline/llm/service.py",
}


def main(argv: list[str]) -> int:
    offenders: list[Path] = []
    for arg in argv:
        p = Path(arg)
        if p.name in FORBIDDEN_FILENAMES and str(p) not in ALLOWLIST:
            offenders.append(p)
    if not offenders:
        return 0
    print("ERRO: filename(s) genérico(s) proibido(s) (CLAUDE.md §Code style):", file=sys.stderr)
    for p in offenders:
        print(f"  {p}", file=sys.stderr)
    print(
        "\nRegra: prefira nomes específicos que retornem <5 hits em grep -r.\n"
        "Ex: `EmergencyReserveCalculator.py` não `ReserveHelper.py`;\n"
        "    `bank_parser.py` não `utils.py`.\n"
        "Se a intenção é helpers privados de aggregate, use `_helpers.py` ou prefixo\n"
        "(ex: `audit_helpers.py`, `format_helpers.py`).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
