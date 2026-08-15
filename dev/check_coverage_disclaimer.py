#!/usr/bin/env python3
"""Gate: superfície que cita cobertura recomendada carrega a ressalva (A40.l60).

A classe re-armou quando o disclaimer nasceu nos cards da S9 e o conselho
migrou para `pontos_urgentes` e para a narrativa. Enumerar call-sites à mão
repete o defeito. Este gate varre as superfícies do relatório e hard-falha
quando o padrão de conselho aparece sem a marca fiduciária.

Prova por mutação: `tests/dev/test_check_coverage_disclaimer.py` injeta um
arquivo órfão e exige EXIT≠0.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MARK = "não constitui recomendação fiduciária"
TS_HOOK = "fiduciaryDisclaimer("
PY_HOOK = "fiduciary_disclaimer("

RECOMMENDATION = re.compile(
    r"cobertura recomendada|contratar seguro|seguro de vida e invalidez|" r"seguro term",
    re.IGNORECASE,
)

SCAN_ROOTS = (
    REPO / "frontend/src/components/report",
    REPO / "pipeline/domain/services/narrativas",
)
SUFFIXES = {".ts", ".tsx", ".py"}


def iter_surfaces(roots: tuple[Path, ...] = SCAN_ROOTS) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        files.extend(path for path in root.rglob("*") if path.suffix in SUFFIXES)
    return sorted(files)


def cites_coverage(text: str) -> bool:
    return RECOMMENDATION.search(text) is not None


def has_disclaimer(text: str) -> bool:
    return MARK in text or TS_HOOK in text or PY_HOOK in text


def offenders(roots: tuple[Path, ...] = SCAN_ROOTS) -> list[Path]:
    bad: list[Path] = []
    for path in iter_surfaces(roots):
        text = path.read_text(encoding="utf-8")
        if cites_coverage(text) and not has_disclaimer(text):
            bad.append(path)
    return bad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, action="append")
    args = parser.parse_args(argv)
    roots = tuple(args.root) if args.root else SCAN_ROOTS
    bad = offenders(roots)
    if not bad:
        return 0
    print("cobertura recomendada sem ressalva fiduciária (A40.l60 · ADR-192):", file=sys.stderr)
    for path in bad:
        print(f"  {path.relative_to(REPO) if path.is_relative_to(REPO) else path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
