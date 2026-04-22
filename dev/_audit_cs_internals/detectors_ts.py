"""Detectores T1-T5 (TypeScript/TSX)."""

from __future__ import annotations

from pathlib import Path

from dev._audit_cs_internals.models import (
    FORBIDDEN_TS_FILENAMES,
    REPO_ROOT,
    TS_ANY_PATTERN,
    TS_FUNC_PATTERN,
    TS_HEX_PATTERN,
    Offender,
)


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def detect_ts_any(path: Path, src: str) -> list[Offender]:
    """T1: any explícito em TS/TSX (CLAUDE.md 'sem any')."""
    out: list[Offender] = []
    rel = _rel(path)
    for i, line in enumerate(src.splitlines(), start=1):
        if _is_disabled_line(line):
            continue
        if TS_ANY_PATTERN.search(line):
            out.append(
                Offender(
                    id="",
                    category="T1_ts_any",
                    severity="high",
                    file=rel,
                    line_start=i,
                    line_end=i,
                    length=1,
                    identifier=line.strip()[:80],
                    message="any explícito; use unknown+narrow ou tipo concreto",
                )
            )
    return out


def _is_disabled_line(line: str) -> bool:
    return "// eslint-disable" in line or "@ts-ignore" in line or "@ts-expect-error" in line


def detect_ts_long_file(path: Path, src: str) -> list[Offender]:
    """T2: arquivos TS >500 linhas."""
    lines = src.count("\n") + 1
    if lines <= 500:
        return []
    rel = _rel(path)
    severity = "high" if lines > 1000 else "med"
    return [
        Offender(
            id="",
            category="T2_ts_long_files",
            severity=severity,
            file=rel,
            line_start=1,
            line_end=lines,
            length=lines,
            identifier=Path(rel).name,
            message=f"TS file {lines} lines; max 500",
        )
    ]


def detect_ts_long_functions(path: Path, src: str) -> list[Offender]:
    """T3: funções TS >20 linhas (heurística brace-matched)."""
    rel = _rel(path)
    lines = src.splitlines()
    out: list[Offender] = []
    for match in TS_FUNC_PATTERN.finditer(src):
        maybe = _ts_long_fn_offender(match, src, lines, rel)
        if maybe is not None:
            out.append(maybe)
    return out


def _ts_long_fn_offender(match, src: str, lines: list[str], rel: str) -> Offender | None:
    name = match.group(1) or match.group(2) or "<anon>"
    start_line = src[: match.start()].count("\n") + 1
    end_line = _find_body_end(lines, start_line - 1)
    if end_line is None:
        return None
    length = end_line - start_line + 1
    if length <= 20:
        return None
    severity = "high" if length > 40 else "med"
    return Offender(
        id="",
        category="T3_ts_long_functions",
        severity=severity,
        file=rel,
        line_start=start_line,
        line_end=end_line,
        length=length,
        identifier=name,
        message=f"TS function {length} lines; max 20 (heurística brace-matched)",
    )


def _find_body_end(lines: list[str], start_idx: int) -> int | None:
    depth = 0
    opened = False
    limit = min(len(lines), start_idx + 400)
    for i in range(start_idx, limit):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
                if opened and depth == 0:
                    return i + 1
    return None


def detect_ts_forbidden_filename(path: Path) -> list[Offender]:
    """T4: filenames genéricos em frontend/src/."""
    rel = _rel(path)
    name = Path(rel).name
    if name not in FORBIDDEN_TS_FILENAMES:
        return []
    return [
        Offender(
            id="",
            category="T4_ts_forbidden_filename",
            severity="med",
            file=rel,
            line_start=1,
            line_end=1,
            length=1,
            identifier=name,
            message=f"Filename '{name}' é genérico; use nome específico",
        )
    ]


def detect_ts_hex_colors(path: Path, src: str) -> list[Offender]:
    """T5: hex color literal em .tsx (ADR-076 — use var(--brand-*))."""
    rel = _rel(path)
    if not rel.endswith(".tsx") or rel.startswith("design-tokens/"):
        return []
    out: list[Offender] = []
    for i, line in enumerate(src.splitlines(), start=1):
        if _hex_is_commented(line):
            continue
        for match in TS_HEX_PATTERN.finditer(line):
            hex_val = match.group(0)
            if len(hex_val) not in (4, 5, 7, 9):
                continue
            out.append(
                Offender(
                    id="",
                    category="T5_ts_hex_colors",
                    severity="med",
                    file=rel,
                    line_start=i,
                    line_end=i,
                    length=1,
                    identifier=hex_val,
                    message=f"Hex color '{hex_val}'; use var(--brand-*) (ADR-076)",
                )
            )
    return out


def _hex_is_commented(line: str) -> bool:
    slash = line.find("//")
    hash_ = line.find("#")
    return 0 <= slash < hash_ if slash >= 0 and hash_ >= 0 else False
