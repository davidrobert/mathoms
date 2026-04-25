#!/usr/bin/env python3
"""Audita ocorrências de identificadores legados de stage (ADR-093 / Fase 9).

Inventaria todas as menções dos nomes legados (`E2`, `E3`, `E5`, `E5.N`,
`E7-apply`, ...) em código, filenames, testes, docs, configs e migrations.
F9.0 usa esta ferramenta como gate inicial; F9.1-F9.6 a re-rodam para
confirmar redução de ofensores.

Exit 0 sempre — esta ferramenta é descritiva, não enforcement (gate é em
``tests/unit/pipeline/test_no_legacy_stage_names.py``).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.stage_spec import (  # noqa: E402
    STAGE_REGISTRY,
    STAGE_RENAME_MAP,
    VIRTUAL_ARTIFACT_STAGES,
)

LEGACY_NAMES = sorted(STAGE_RENAME_MAP.keys(), key=lambda s: (-len(s), s))

CATEGORIES = (
    "code_string",
    "code_identifier",
    "filename",
    "test_string",
    "doc_string",
    "config",
    "alembic",
    "db_value",
)


@dataclass
class Occurrence:
    name: str
    category: str
    path: str
    line: int
    snippet: str


@dataclass
class AuditReport:
    generated_at: str
    total: int
    by_category: dict[str, int] = field(default_factory=dict)
    by_name: dict[str, int] = field(default_factory=dict)
    top_files: list[tuple[str, int]] = field(default_factory=list)
    pipeline_stage_files: list[str] = field(default_factory=list)
    scripts_stage_files: list[str] = field(default_factory=list)
    coverage: dict[str, bool] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    db_distinct_stages: list[str] | None = None
    occurrences: list[Occurrence] = field(default_factory=list)


SCAN_DIRS = (
    "pipeline",
    "scripts",
    "backend",
    "tests",
    "config",
    "docs",
    "dev",
    "frontend/src",
)

CODE_EXTS = {".py", ".ts", ".tsx", ".js", ".go"}
DOC_EXTS = {".md"}
CONFIG_EXTS = {".json", ".yaml", ".yml"}


def _iter_files():
    for root in SCAN_DIRS:
        rp = REPO_ROOT / root
        if not rp.exists():
            continue
        for p in rp.rglob("*"):
            if not p.is_file():
                continue
            if any(part in {"__pycache__", ".venv", "node_modules", ".next"} for part in p.parts):
                continue
            if p.suffix not in CODE_EXTS | DOC_EXTS | CONFIG_EXTS:
                continue
            yield p


def _classify(rel: str, suffix: str) -> str:
    if suffix in DOC_EXTS:
        return "doc_string"
    if suffix in CONFIG_EXTS:
        return "config"
    if rel.startswith("backend/alembic/versions/"):
        return "alembic"
    if rel.startswith("tests/") or rel.startswith("backend/tests/"):
        return "test_string"
    return "code_string"


def _build_patterns() -> dict[str, re.Pattern[str]]:
    return {
        name: re.compile(rf"(?<![A-Za-z0-9_\-\.]){re.escape(name)}(?![A-Za-z0-9_])")
        for name in LEGACY_NAMES
    }


def _scan_filenames() -> list[Occurrence]:
    out: list[Occurrence] = []
    pat = re.compile(r"(?:^|/)e(\d+(?:_\d+)?)_[a-z][a-z0-9_]*\.py$")
    for sub in ("scripts", "pipeline/stages"):
        rp = REPO_ROOT / sub
        if not rp.exists():
            continue
        for p in rp.rglob("*.py"):
            rel = p.relative_to(REPO_ROOT).as_posix()
            if pat.search(rel):
                out.append(
                    Occurrence(
                        name=rel.split("/")[-1].split("_")[0],
                        category="filename",
                        path=rel,
                        line=0,
                        snippet=rel,
                    )
                )
    return out


def _scan_text() -> list[Occurrence]:
    patterns = _build_patterns()
    code_id_patterns = {
        name: re.compile(
            rf"\b[A-Za-z_][A-Za-z0-9_]*{re.escape(name.replace('-', '_').replace('.', '_'))}[A-Za-z0-9_]*\b"
        )
        for name in LEGACY_NAMES
    }
    occs: list[Occurrence] = []
    for p in _iter_files():
        rel = p.relative_to(REPO_ROOT).as_posix()
        suffix = p.suffix
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        category = _classify(rel, suffix)
        for i, line in enumerate(text.splitlines(), start=1):
            for name, pat in patterns.items():
                if pat.search(line):
                    occs.append(
                        Occurrence(
                            name=name,
                            category=category,
                            path=rel,
                            line=i,
                            snippet=line.strip()[:140],
                        )
                    )
    return occs


def _scan_db() -> list[str] | None:
    try:
        from sqlalchemy import text  # type: ignore

        from backend.app.db import session_scope  # type: ignore
    except Exception:
        return None
    try:
        with session_scope() as s:
            rows = s.execute(text("SELECT DISTINCT stage FROM pipeline_artifacts")).all()
        return sorted(r[0] for r in rows if r[0])
    except Exception:
        return None


def _summarize(occurrences: list[Occurrence], db_stages: list[str] | None) -> AuditReport:
    by_category: dict[str, int] = defaultdict(int)
    by_name: dict[str, int] = defaultdict(int)
    by_file: dict[str, int] = defaultdict(int)
    for o in occurrences:
        by_category[o.category] += 1
        by_name[o.name] += 1
        by_file[o.path] += 1
    pipe_files = sorted(
        {
            o.path
            for o in occurrences
            if o.category == "filename" and o.path.startswith("pipeline/stages/")
        }
    )
    scripts_files = sorted(
        {o.path for o in occurrences if o.category == "filename" and o.path.startswith("scripts/")}
    )
    # Coverage: só conta nomes que apareceram em strings/configs/docs/alembic/db.
    # Filenames (`e2_extract.py`) não são strings de stage e não participam.
    string_categories = {
        "code_string",
        "test_string",
        "doc_string",
        "config",
        "alembic",
        "db_value",
    }
    string_names: set[str] = {o.name for o in occurrences if o.category in string_categories}
    coverage = {n: (n in STAGE_RENAME_MAP) for n in sorted(string_names)}
    blockers: list[str] = []
    for n, mapped in coverage.items():
        if not mapped:
            blockers.append(
                f"Nome '{n}' aparece em string de produção mas não está em STAGE_RENAME_MAP"
            )
    if db_stages is not None:
        for st in db_stages:
            if st not in STAGE_RENAME_MAP:
                blockers.append(f"DB tem stage '{st}' não presente em STAGE_RENAME_MAP")
    top = sorted(by_file.items(), key=lambda kv: -kv[1])[:20]
    return AuditReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        total=len(occurrences),
        by_category=dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
        by_name=dict(sorted(by_name.items(), key=lambda kv: -kv[1])),
        top_files=top,
        pipeline_stage_files=pipe_files,
        scripts_stage_files=scripts_files,
        coverage=coverage,
        blockers=blockers,
        db_distinct_stages=db_stages,
        occurrences=occurrences,
    )


def _render_md(rep: AuditReport) -> str:
    lines = [
        f"# Stage Audit (F9.0) — {rep.generated_at}",
        "",
        f"**Total ocorrências**: {rep.total}",
        f"**Blockers**: {len(rep.blockers)}",
        "",
        "## Por categoria",
        "",
        "| Categoria | Ocorrências |",
        "| --- | ---: |",
    ]
    for cat, n in rep.by_category.items():
        lines.append(f"| {cat} | {n} |")
    lines += [
        "",
        "## Por nome legado",
        "",
        "| Nome | Ocorrências | Mapeado? |",
        "| --- | ---: | :---: |",
    ]
    for name, n in rep.by_name.items():
        lines.append(f"| `{name}` | {n} | {'✅' if rep.coverage.get(name) else '❌'} |")
    lines += ["", "## Top 20 arquivos", "", "| Arquivo | Ocorrências |", "| --- | ---: |"]
    for path, n in rep.top_files:
        lines.append(f"| `{path}` | {n} |")
    lines += ["", "## Filenames `e*` em pipeline/stages/", ""]
    lines += [f"- `{p}`" for p in rep.pipeline_stage_files] or ["_(nenhum)_"]
    lines += ["", "## Filenames `e*` em scripts/", ""]
    lines += [f"- `{p}`" for p in rep.scripts_stage_files] or ["_(nenhum)_"]
    if rep.db_distinct_stages is not None:
        lines += ["", "## DB — `SELECT DISTINCT stage FROM pipeline_artifacts`", ""]
        if rep.db_distinct_stages:
            lines += [
                f"- `{s}` → `{STAGE_RENAME_MAP.get(s, '❌ NÃO MAPEADO')}`"
                for s in rep.db_distinct_stages
            ]
        else:
            lines.append("_(DB vazio)_")
    else:
        lines += ["", "## DB", "", "_DB indisponível ou backend não importável — pular check._"]
    if rep.blockers:
        lines += ["", "## ⚠️ Blockers", ""]
        lines += [f"- {b}" for b in rep.blockers]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "_scratch")
    parser.add_argument("--format", choices=("json", "md", "both"), default="both")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--skip-db", action="store_true")
    args = parser.parse_args(argv)

    occs = _scan_text() + _scan_filenames()
    db = None if args.skip_db else _scan_db()
    rep = _summarize(occs, db)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = args.output_dir / f"stage_audit_{args.date}"

    if args.format in {"json", "both"}:
        payload = asdict(rep)
        # Trim occurrences in JSON to limit size — keep first 500
        payload["occurrences"] = payload["occurrences"][:500]
        (base.with_suffix(".json")).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"json: {base.with_suffix('.json')}")
    if args.format in {"md", "both"}:
        (base.with_suffix(".md")).write_text(_render_md(rep), encoding="utf-8")
        print(f"md:   {base.with_suffix('.md')}")
    print(f"total={rep.total} blockers={len(rep.blockers)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
