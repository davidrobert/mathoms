#!/usr/bin/env python3
"""Cross-checks deterministicos da F3.a da rodada unificada. Read-only."""

# Promovido do diretorio da rodada para `dev/` no `U4`, pagando o item 2 do §10
# do `U3`: instrumento executavel versionado, diffavel e gateado. Copiar o `.py`
# da rodada anterior fez o `U3` herdar a versao pre-conserto e comparar zero
# celulas em 2 baldes imprimindo verde.
#
# Rodar da raiz do checkout principal, com o DB pinado em ABSOLUTO:
#     MATHOMS_DATABASE_URL=sqlite+aiosqlite:////<abs>/mathoms.db \
#       .venv/bin/python dev/unified_xchecks.py <ws> <run_id> <check> [args]
#
# checks: x5 | x2 | x3 | x3b | x4 | sonda
# (o `e2` vive em `dev/unified_e2_snapshot.py --compare`, que devolve exit code)

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev._unified_xchecks.ancoragem import sonda, x4  # noqa: E402
from dev._unified_xchecks.base import procedencia, veredito  # noqa: E402
from dev._unified_xchecks.execucao import x5  # noqa: E402
from dev._unified_xchecks.razao import x2, x3, x3b  # noqa: E402

__all__ = ["procedencia", "sonda", "veredito", "x2", "x3", "x3b", "x4", "x5"]


def main(argv: list[str]) -> int:
    ws, run, check, *rest = argv
    procedencia(__file__)
    despacho = {
        "x5": lambda: x5(ws, run),
        "x2": lambda: x2(ws, run),
        "x3": lambda: x3(ws, run, rest[0]),
        "x3b": lambda: x3b(ws, run),
        "x4": lambda: x4(ws, run, rest[0], rest[1]),
        "sonda": lambda: sonda(ws, run),
    }
    despacho[check]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
