#!/usr/bin/env python3
"""Gate ADR-381 D1: `hidden md:*` em dado do relatório some do PDF.

A caixa de página A4 tem 703px, então `md:` (768px) nunca casa no papel.
`hidden md:block` escrito como "variante desktop" entrega o mobile — ou
some sem par. Variante que o papel deve receber usa `sm:` (640px) ou
`@media print` (`print:table-cell`). Chrome de app e dialog ficam em
`md:` e entram no allowlist nomeado.

Prova por mutação: `tests/dev/test_check_hidden_md_on_paper.py` injeta
um `hidden md:block` sem `print:` e exige EXIT≠0.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO / "frontend/src/components/report"
SUFFIXES = {".ts", ".tsx"}

# Superfície que NÃO é papel: ToC/chrome do shell e dialog fechado.
# Path relativo a `frontend/src/components/report/`.
ALLOWLIST = frozenset(
    {
        "ReportShell.tsx",
        "shell/ReportActions.tsx",
        "RealEstateBreakdownPanel.tsx",
    }
)

# `hidden … md:block|table|table-cell|grid|flex|inline-*` — o display só
# aparece a partir de 768px. `md:hidden` é o par que some no desktop e
# portanto é o que o papel recebe; em dado isso é o stack, não a tabela.
HIDE_UNTIL_MD = re.compile(
    r"hidden(?:\s+[A-Za-z0-9:\[\]/%_.-]+)*\s+md:(?:block|table|table-cell|grid|flex|inline-block|inline-flex)"
    r"|md:hidden"
)

# Companheiro que desoculta no papel. Tem de estar NA MESMA linha — o
# `print:table-cell` do Top15 mora no mesmo className que o `md:table-cell`.
PRINT_UNHIDE = re.compile(r"print:(?:block|table|table-cell|grid|flex|inline-block|inline-flex)")


def iter_surfaces(root: Path = SCAN_ROOT) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.suffix in SUFFIXES)


def rel_report(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def line_offends(line: str) -> bool:
    if not HIDE_UNTIL_MD.search(line):
        return False
    return PRINT_UNHIDE.search(line) is None


def offenders(root: Path = SCAN_ROOT) -> list[tuple[Path, int, str]]:
    found: list[tuple[Path, int, str]] = []
    for path in iter_surfaces(root):
        if rel_report(path, root) in ALLOWLIST:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line_offends(line):
                found.append((path, lineno, line.strip()))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=SCAN_ROOT)
    args = parser.parse_args(argv)
    bad = offenders(args.root)
    if not bad:
        return 0
    print(
        "hidden md:* sem print: em superfície de dado do relatório "
        "(A40.l54 · ADR-381 D1) — o PDF (703px) nunca casa md: (768px):",
        file=sys.stderr,
    )
    for path, lineno, text in bad:
        shown = path.relative_to(REPO) if path.is_relative_to(REPO) else path
        print(f"  {shown}:{lineno}: {text}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
