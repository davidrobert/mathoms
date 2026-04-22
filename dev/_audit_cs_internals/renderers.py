"""JSON + Markdown renderers (A6g.1)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

from dev._audit_cs_internals.models import REPO_ROOT, SEVERITY_RANK, Offender, Summary


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_json(offenders: list[Offender], summary: Summary, commit: str) -> str:
    """Canonical JSON output com ordenação estável."""
    doc = {
        "audit_version": "1.0",
        "generated_at": _now_iso(),
        "git_commit": commit,
        "repo_root": str(REPO_ROOT),
        "summary": _summary_dict(summary),
        "offenders": [asdict(o) for o in offenders],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def _summary_dict(summary: Summary) -> dict[str, object]:
    sev = dict(
        sorted(summary.offenders_by_severity.items(), key=lambda kv: SEVERITY_RANK.get(kv[0], 99))
    )
    by_dir = {k: dict(sorted(v.items())) for k, v in sorted(summary.offenders_by_directory.items())}
    return {
        "files_scanned": {
            "python": summary.files_scanned_python,
            "typescript": summary.files_scanned_typescript,
        },
        "offenders_by_category": dict(sorted(summary.offenders_by_category.items())),
        "offenders_by_severity": sev,
        "offenders_by_directory": by_dir,
    }


def render_markdown(offenders: list[Offender], summary: Summary, commit: str) -> str:
    """Markdown human-readable com top-50 por categoria + pivot."""
    parts: list[str] = []
    parts.extend(_md_header(offenders, summary, commit))
    parts.extend(["## Sumário por categoria", "", _render_category_table(offenders, summary), ""])
    parts.extend(["## Sumário por severidade", "", _render_severity_table(summary), ""])
    parts.extend(["## Top ofensores (prioridade de sweep)", "", _render_top_offenders(offenders)])
    parts.extend(["## Pivot por diretório", "", _render_directory_pivot(summary), ""])
    return "\n".join(parts)


def _md_header(offenders: list[Offender], summary: Summary, commit: str) -> list[str]:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [
        f"# Code Style Audit — {date}",
        "",
        f"Commit: `{commit[:7]}`  ",
        f"Files scanned: {summary.files_scanned_python} Python + {summary.files_scanned_typescript} TypeScript  ",
        f"Total offenders: {len(offenders)}",
        "",
    ]


def _render_category_table(offenders: list[Offender], summary: Summary) -> str:
    rows = ["| Categoria | Count | High+ |", "|---|---|---|"]
    for cat, count in sorted(summary.offenders_by_category.items()):
        high_plus = sum(
            1 for o in offenders if o.category == cat and SEVERITY_RANK[o.severity] <= 1
        )
        rows.append(f"| {cat} | {count} | {high_plus} |")
    return "\n".join(rows)


def _render_severity_table(summary: Summary) -> str:
    rows = ["| Severidade | Count |", "|---|---|"]
    for sev in ("critical", "high", "med", "low", "info"):
        rows.append(f"| {sev} | {summary.offenders_by_severity.get(sev, 0)} |")
    return "\n".join(rows)


def _render_top_offenders(offenders: list[Offender]) -> str:
    groups: dict[str, list[Offender]] = {}
    for off in offenders:
        groups.setdefault(off.category, []).append(off)
    chunks: list[str] = []
    for cat in sorted(groups.keys()):
        chunks.append(f"### {cat}")
        chunks.append("")
        items = sorted(groups[cat], key=lambda o: (SEVERITY_RANK[o.severity], -o.length, o.file))[
            :10
        ]
        for off in items:
            mark = " *(allowlisted)*" if off.allowlisted else ""
            chunks.append(
                f"- `{off.file}:{off.line_start}` **{off.severity}** · `{off.identifier}` · len={off.length}{mark}"
            )
        chunks.append("")
    return "\n".join(chunks)


def _render_directory_pivot(summary: Summary) -> str:
    cats = sorted({c for per in summary.offenders_by_directory.values() for c in per})
    if not cats:
        return "_nenhum ofensor_"
    header = "| Diretório | " + " | ".join(cats) + " | total |"
    sep = "|" + "---|" * (len(cats) + 2)
    rows = [header, sep]
    for dir_, per in sorted(summary.offenders_by_directory.items()):
        total = sum(per.values())
        cells = [str(per.get(c, 0)) for c in cats]
        rows.append(f"| {dir_} | " + " | ".join(cells) + f" | {total} |")
    return "\n".join(rows)
