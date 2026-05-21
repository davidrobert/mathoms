#!/usr/bin/env python3
"""ADR-235 · A16 — gate: switch/match sobre `classification` exige default."""

# Motivo: enum classification (ADR-215 + ADR-235) cresce. Reader exhaustive
# sem default quebra silenciosamente (TS narrow para never; Python match
# sem case _). Fail-fast > fail-silent. Heurística sem AST. Skip:
# comentários, generated/, tests/, playwright/, node_modules/, .claude/, docs/.

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = (
    "frontend/src/generated/",
    "backend/app/generated/",
    "tests/",
    "backend/tests/",
    "frontend/playwright/",
    "node_modules/",
    ".claude/",
    "docs/",
)

SWITCH_RE = re.compile(
    r"\bswitch\s*\(\s*(?:[a-zA-Z_$][\w$]*\s*\.\s*)?classification\s*\)",
)
MATCH_RE = re.compile(
    r"^\s*match\s+(?:[a-zA-Z_][\w]*\s*\.\s*)?classification\s*:",
    re.MULTILINE,
)
TS_DEFAULT_RE = re.compile(r"\bdefault\s*:")
PY_CASE_DEFAULT_RE = re.compile(r"^\s*case\s+_\s*[:|]", re.MULTILINE)


def _should_skip(path: Path) -> bool:
    p = path.as_posix()
    if path.name == "check_classification_exhaustive.py":
        return True
    return any(skip in p for skip in SKIP_DIRS)


def _strip_ts_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//.*?$", "", source, flags=re.MULTILINE)


def _strip_py_comments(source: str) -> str:
    return re.sub(r"#.*?$", "", source, flags=re.MULTILINE)


def _scan_ts_block(source: str, open_idx: int) -> str:
    """Devolve substring delimitada por `{...}` casado começando em open_idx."""
    depth = 1
    i = open_idx + 1
    while i < len(source) and depth > 0:
        c = source[i]
        depth += 1 if c == "{" else -1 if c == "}" else 0
        i += 1
    return source[open_idx:i]


def _find_block_after(source: str, start: int) -> str:
    """Devolve o bloco `{...}` que segue ``start`` (TS)."""
    open_idx = source.find("{", start)
    if open_idx == -1:
        return ""
    return _scan_ts_block(source, open_idx)


def _line_indent(source: str, pos: int) -> str:
    line_start = source.rfind("\n", 0, pos) + 1
    raw = source[line_start:pos]
    return raw[: len(raw) - len(raw.lstrip(" \t"))]


def _take_indented_block(lines: list[str], base_len: int) -> list[str]:
    """Pega linhas até encontrar uma com indent <= base_len (Python)."""
    out: list[str] = []
    for line in lines:
        stripped = line.lstrip(" \t")
        if stripped in ("", "\n"):
            out.append(line)
            continue
        line_indent = len(line) - len(stripped)
        if line_indent <= base_len:
            break
        out.append(line)
    return out


def _find_match_block(source: str, match_start: int) -> str:
    """Devolve o bloco indentado que segue ``match X:`` em Python."""
    indent = _line_indent(source, match_start)
    lines = source[match_start:].splitlines(keepends=True)
    body = _take_indented_block(lines[1:], len(indent))
    return lines[0] + "".join(body)


def _check_ts(path: Path, source: str) -> list[str]:
    stripped = _strip_ts_comments(source)
    errors: list[str] = []
    for m in SWITCH_RE.finditer(stripped):
        block = _find_block_after(stripped, m.end())
        if TS_DEFAULT_RE.search(block):
            continue
        line_no = stripped.count("\n", 0, m.start()) + 1
        errors.append(
            f"{path}:{line_no}: `switch (classification)` sem `default:` "
            f"— adicione branch default (ADR-235 §Riscos)."
        )
    return errors


def _check_py(path: Path, source: str) -> list[str]:
    stripped = _strip_py_comments(source)
    errors: list[str] = []
    for m in MATCH_RE.finditer(stripped):
        block = _find_match_block(stripped, m.start())
        if PY_CASE_DEFAULT_RE.search(block):
            continue
        line_no = stripped.count("\n", 0, m.start()) + 1
        errors.append(
            f"{path}:{line_no}: `match classification:` sem `case _:` "
            f"— adicione branch default (ADR-235 §Riscos)."
        )
    return errors


def _check_file(path: Path) -> list[str]:
    if _should_skip(path):
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    if path.suffix in (".ts", ".tsx", ".js", ".jsx"):
        return _check_ts(path, source)
    if path.suffix == ".py":
        return _check_py(path, source)
    return []


def _discover_repo() -> list[Path]:
    found: list[Path] = []
    for pattern in ("frontend/src/**/*.ts", "frontend/src/**/*.tsx"):
        found.extend(Path(".").glob(pattern))
    for pattern in ("backend/app/**/*.py", "pipeline/**/*.py", "scripts/**/*.py"):
        found.extend(Path(".").glob(pattern))
    return found


def main(argv: list[str]) -> int:
    files = [Path(p) for p in argv] if argv else _discover_repo()
    errors = [e for f in files for e in _check_file(f)]
    if not errors:
        return 0
    print("ERRO: gate classification exhaustive (ADR-235) — falhou:", file=sys.stderr)
    for e in errors:
        print(f"  • {e}", file=sys.stderr)
    print(
        "\nEnum `classification` (ADR-215+ADR-235) cresce; "
        "switches/matches DEVEM ter branch default explícito.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
