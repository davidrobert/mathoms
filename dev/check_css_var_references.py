#!/usr/bin/env python3
"""Gate: ``var(--xxx)`` referenciado em ``frontend/src/**`` deve existir.

Parsea declarações ``--xxx:`` em ``frontend/src/styles/tokens.css`` +
``frontend/src/app/globals.css`` (escopo onde os tokens vivem); varre
``frontend/src/**/*.{tsx,ts,css}`` por ``var(--xxx)`` literais; falha
se algum consumidor referencia token não declarado.

Uso:
    python3 dev/check_css_var_references.py
    python3 dev/check_css_var_references.py --list-tokens

Exit 0 = OK, 1 = referência fantasma encontrada.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN_SOURCES = (
    ROOT / "frontend" / "src" / "styles" / "tokens.css",
    ROOT / "frontend" / "src" / "app" / "globals.css",
)
SCAN_ROOT = ROOT / "frontend" / "src"
SCAN_GLOBS = ("**/*.tsx", "**/*.ts", "**/*.css")

# Tokens injetados em runtime (não declarados em CSS estático).
# - --font-* vêm de next/font/google (frontend/src/app/layout.tsx).
# - --radix-* vêm dos componentes do Radix UI em runtime.
RUNTIME_TOKENS: frozenset[str] = frozenset(
    {
        "font-body",
        "font-display",
        "font-mono",
    }
)
RUNTIME_PREFIXES: tuple[str, ...] = ("radix-",)

DECLARATION_RE = re.compile(r"--([a-z][a-z0-9-]*)\s*:", re.IGNORECASE)
REFERENCE_RE = re.compile(r"var\(\s*--([a-z][a-z0-9-]*)\s*[,)]", re.IGNORECASE)
JSDOC_LINE_RE = re.compile(r"^\s*\*")
SINGLE_LINE_COMMENT_RE = re.compile(r"^\s*//")


def is_runtime(name: str) -> bool:
    if name in RUNTIME_TOKENS:
        return True
    return any(name.startswith(prefix) for prefix in RUNTIME_PREFIXES)


def declared_tokens(paths: tuple[Path, ...]) -> set[str]:
    declared: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for match in DECLARATION_RE.finditer(path.read_text(encoding="utf-8")):
            declared.add(match.group(1))
    return declared


def is_comment_line(line: str) -> bool:
    return bool(JSDOC_LINE_RE.match(line) or SINGLE_LINE_COMMENT_RE.match(line))


def scan_file(path: Path, declared: set[str]) -> list[str]:
    out: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if is_comment_line(line):
            continue
        for match in REFERENCE_RE.finditer(line):
            name = match.group(1)
            if name in declared or is_runtime(name):
                continue
            rel = path.relative_to(ROOT)
            out.append(f"{rel}:{lineno} -> var(--{name}) NOT in tokens.css/globals.css")
    return out


def collect_violations(declared: set[str]) -> list[str]:
    errors: list[str] = []
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in SCAN_ROOT.glob(pattern):
            if path in seen or "node_modules" in path.parts:
                continue
            seen.add(path)
            errors.extend(scan_file(path, declared))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-tokens", action="store_true", help="Print declared tokens and exit."
    )
    args = parser.parse_args(argv)

    declared = declared_tokens(TOKEN_SOURCES)

    if args.list_tokens:
        for name in sorted(declared):
            print(f"--{name}")
        return 0

    errors = collect_violations(declared)
    for line in errors:
        print(line, file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} phantom var(--xxx) reference(s) found.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
