#!/usr/bin/env python3
"""Audit code style drift vs CLAUDE.md §Code style (A6g.1).

Mede ofensores em Python (P1-P10) e TypeScript (T1-T5), emite JSON + Markdown
top-ofensores. Informativo; --strict sai 1 se houver ofensor >= med. Regras:
CLAUDE.md §Code style; detectores em dev/_audit_cs_internals/.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev._audit_cs_internals.models import AuditConfig, Offender, Summary
from dev._audit_cs_internals.renderers import render_json, render_markdown
from dev._audit_cs_internals.runner import git_commit, has_blocking, run_audit


def _parse_args(argv: list[str] | None) -> AuditConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "_scratch")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--format", choices=("json", "md", "both"), default="both")
    parser.add_argument("--category", default="", help="Comma-separated codes (P1,P2,T1,...)")
    parser.add_argument("--severity", default="", help="Comma-separated severities")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any offender >= med")
    parser.add_argument("--path", type=Path, default=None, help="Restrict to file or directory")
    args = parser.parse_args(argv)
    return AuditConfig(
        output_dir=args.output_dir,
        date=args.date,
        format=args.format,
        categories=frozenset(c.strip() for c in args.category.split(",") if c.strip()),
        severities=frozenset(s.strip() for s in args.severity.split(",") if s.strip()),
        strict=args.strict,
        path=args.path.resolve() if args.path else None,
    )


def _write_outputs(config: AuditConfig, offenders: list[Offender], summary: Summary) -> list[Path]:
    commit = git_commit()
    written: list[Path] = []
    config.output_dir.mkdir(parents=True, exist_ok=True)
    stem = config.output_dir / f"code_style_audit_{config.date}"
    if config.format in ("json", "both"):
        json_path = stem.with_suffix(".json")
        json_path.write_text(render_json(offenders, summary, commit), encoding="utf-8")
        written.append(json_path)
    if config.format in ("md", "both"):
        md_path = stem.with_suffix(".md")
        md_path.write_text(render_markdown(offenders, summary, commit), encoding="utf-8")
        written.append(md_path)
    return written


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)
    offenders, summary = run_audit(config)
    written = _write_outputs(config, offenders, summary)
    print(
        f"Scanned {summary.files_scanned_python} py + "
        f"{summary.files_scanned_typescript} ts; {len(offenders)} offenders.",
        file=sys.stderr,
    )
    for path in written:
        print(f"wrote {_display_path(path)}", file=sys.stderr)
    if config.strict and has_blocking(offenders):
        return 1
    return 0


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
