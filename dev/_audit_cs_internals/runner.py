"""Orquestração: percorre arquivos, roda detectores, agrega summary (A6g.1)."""

from __future__ import annotations

import subprocess
from dataclasses import asdict
from pathlib import Path

from dev._audit_cs_internals.detectors_py import (
    detect_deep_nesting,
    detect_dict_str_any_boundary,
    detect_float_money,
    detect_forbidden_names,
    detect_long_file,
    detect_long_functions,
    detect_multiparagraph_docstring,
    detect_optional_without_default,
    detect_pipeline_boundary,
    detect_what_comments,
    parse_ast,
)
from dev._audit_cs_internals.detectors_ts import (
    detect_ts_any,
    detect_ts_forbidden_filename,
    detect_ts_hex_colors,
    detect_ts_long_file,
    detect_ts_long_functions,
)
from dev._audit_cs_internals.models import (
    REPO_ROOT,
    SEVERITY_RANK,
    AuditConfig,
    Offender,
    Summary,
)
from dev._audit_cs_internals.walker import collect_python_files, collect_ts_files


def _active(code: str, active: frozenset[str]) -> bool:
    return code in active if active else True


def run_python_detectors(files: list[Path], active: frozenset[str]) -> list[Offender]:
    out: list[Offender] = []
    for path in files:
        tree, src = parse_ast(path)
        if src and _active("P2", active):
            out.extend(detect_long_file(path, src))
        if src and _active("P8", active):
            out.extend(detect_what_comments(path, src))
        if tree is None:
            continue
        out.extend(_run_ast_detectors(path, tree, src, active))
    return out


def _run_ast_detectors(path: Path, tree, src: str, active: frozenset[str]) -> list[Offender]:
    out: list[Offender] = []
    if _active("P1", active):
        out.extend(detect_long_functions(path, tree))
    if _active("P3", active):
        out.extend(detect_dict_str_any_boundary(path, tree))
    if _active("P4", active):
        out.extend(detect_optional_without_default(path, tree, src))
    if _active("P5", active):
        out.extend(detect_float_money(path, tree))
    if _active("P6", active):
        out.extend(detect_forbidden_names(path, tree))
    if _active("P7", active):
        out.extend(detect_multiparagraph_docstring(path, tree))
    if _active("P9", active):
        out.extend(detect_deep_nesting(path, tree))
    return out


def run_typescript_detectors(files: list[Path], active: frozenset[str]) -> list[Offender]:
    out: list[Offender] = []
    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _active("T1", active):
            out.extend(detect_ts_any(path, src))
        if _active("T2", active):
            out.extend(detect_ts_long_file(path, src))
        if _active("T3", active):
            out.extend(detect_ts_long_functions(path, src))
        if _active("T4", active):
            out.extend(detect_ts_forbidden_filename(path))
        if _active("T5", active):
            out.extend(detect_ts_hex_colors(path, src))
    return out


def _severity_allowed(severities: frozenset[str], offender: Offender) -> bool:
    return offender.severity in severities if severities else True


def _assign_ids(offenders: list[Offender]) -> list[Offender]:
    counters: dict[str, int] = {}
    out: list[Offender] = []
    for off in offenders:
        code = off.category.split("_", 1)[0]
        counters[code] = counters.get(code, 0) + 1
        out.append(Offender(**{**asdict(off), "id": f"{code}-{counters[code]:04d}"}))
    return out


def _sort_offenders(offenders: list[Offender]) -> list[Offender]:
    return sorted(offenders, key=lambda o: (SEVERITY_RANK[o.severity], o.file, o.line_start))


def _summarize(offenders: list[Offender], py_count: int, ts_count: int) -> Summary:
    summary = Summary(files_scanned_python=py_count, files_scanned_typescript=ts_count)
    for off in offenders:
        _accumulate_offender(summary, off)
    return summary


def _accumulate_offender(summary: Summary, off: Offender) -> None:
    summary.offenders_by_category[off.category] = (
        summary.offenders_by_category.get(off.category, 0) + 1
    )
    summary.offenders_by_severity[off.severity] = (
        summary.offenders_by_severity.get(off.severity, 0) + 1
    )
    top_dir = off.file.split("/", 1)[0] + "/"
    by_dir = summary.offenders_by_directory.setdefault(top_dir, {})
    by_dir[off.category] = by_dir.get(off.category, 0) + 1


def git_commit() -> str:
    """Returns current HEAD SHA or 'unknown' on failure."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def run_audit(config: AuditConfig) -> tuple[list[Offender], Summary]:
    """Executa todos os detectores habilitados; devolve offenders + summary."""
    py_files = collect_python_files(config)
    ts_files = collect_ts_files(config)
    offenders: list[Offender] = []
    offenders.extend(run_python_detectors(py_files, config.categories))
    if _active("P10", config.categories):
        offenders.extend(detect_pipeline_boundary())
    offenders.extend(run_typescript_detectors(ts_files, config.categories))
    offenders = [o for o in offenders if _severity_allowed(config.severities, o)]
    offenders = _assign_ids(_sort_offenders(offenders))
    summary = _summarize(offenders, len(py_files), len(ts_files))
    return offenders, summary


def has_blocking(offenders: list[Offender]) -> bool:
    """True se há offender >= med não-allowlisted (para --strict)."""
    return any(
        SEVERITY_RANK[o.severity] <= SEVERITY_RANK["med"] and not o.allowlisted for o in offenders
    )
