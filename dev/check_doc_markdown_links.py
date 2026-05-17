#!/usr/bin/env python3
"""Gate progressivo para markdown links relativos em docs/."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

from check_doc_links import (
    DOCS,
    MARKDOWN_LINK_RE,
    REPO_ROOT,
    URI_SCHEME_RE,
    MarkdownLinkRef,
    collect_markdown_files,
    extract_markdown_links,
)

ALLOWLIST = REPO_ROOT / "dev" / "doc_markdown_link_allowlist.txt"
LINE_SUFFIX_RE = re.compile(r":\d+(?:-\d+)?$")

FIX_ALIASES = {
    "BACKLOG.md": DOCS / "BACKLOG.md",
    "DECISIONS.md": DOCS / "DECISIONS.md",
    "SETUP.md": DOCS / "reference" / "SETUP.md",
    "TESTING.md": DOCS / "reference" / "TESTING.md",
    "SMOKE_TEST.md": DOCS / "reference" / "SMOKE_TEST.md",
    "ARCHITECTURE.md": DOCS / "reference" / "ARCHITECTURE.md",
    "CANONICAL_ENGINE_P0.md": DOCS / "reference" / "CANONICAL_ENGINE_P0.md",
    "COPY_GUIDELINES.md": DOCS / "reference" / "COPY_GUIDELINES.md",
    "FORMULAS.md": DOCS / "reference" / "FORMULAS.md",
    "PIPELINE_ARTIFACTS.md": DOCS / "reference" / "PIPELINE_ARTIFACTS.md",
    "RUNBOOK.md": DOCS / "reference" / "RUNBOOK.md",
    "SLO.md": DOCS / "reference" / "SLO.md",
    "SMOKE_TEST_HUMAN.md": DOCS / "reference" / "SMOKE_TEST_HUMAN.md",
    "STATELESS_AUDIT.md": DOCS / "reference" / "STATELESS_AUDIT.md",
    "INTERNAL_ADMIN_ROADMAP.md": DOCS / "plan" / "INTERNAL_ADMIN" / "_README.md",
    "ROADMAP.md": DOCS / "_MOC" / "_generated" / "ROADMAP.md",
    "REPORT_PREMIUM_GAPS.md": DOCS / "plan" / "REPORT_PREMIUM" / "GAPS.md",
    "REPORT_A11Y_CHECKLIST.md": DOCS / "plan" / "REPORT_PREMIUM" / "A11Y_CHECKLIST.md",
    "REPORT_A11Y_GATE_PROOF.md": DOCS / "plan" / "REPORT_PREMIUM" / "A11Y_GATE_PROOF.md",
    "REPORT_MOBILE_SPEC.md": DOCS / "plan" / "REPORT_PREMIUM" / "MOBILE_SPEC.md",
    "REPORT_VISUAL_SNAPSHOTS.md": DOCS / "plan" / "REPORT_PREMIUM" / "VISUAL_SNAPSHOTS.md",
    "CONFIG_CUTOVER_PLAN.md": DOCS / "archive" / "CONFIG_CUTOVER_PLAN-2026-04-27.md",
    "audits/code_style_audit_20260421.md": DOCS
    / "archive"
    / "audits"
    / "code_style_audit_20260421.md",
    "runbooks/cutover.md": DOCS / "archive" / "cutover-2026-05-14.md",
    "runbooks/incidents/": DOCS / "reference" / "runbooks" / "incidents",
    "plan/CATEGORY_OVERRIDES_UX/_README.md": DOCS
    / "archive"
    / "CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md",
    "adr/137-categorization-templates-overrides.md": DOCS
    / "adr"
    / "137-catalog-override-resolver-para-categorization-e.md",
}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    entries: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        source, target, *_ = line.split("\t")
        entries.add(f"{source}\t{target}")
    return entries


def _key(ref: MarkdownLinkRef) -> str:
    return f"{_rel(ref.source)}\t{ref.target}"


def _target_without_line_suffix(target: str) -> str:
    return LINE_SUFFIX_RE.sub("", target)


def _is_relative_target(target: str) -> bool:
    if not target or target.startswith("#"):
        return False
    return not (URI_SCHEME_RE.match(target) or target.startswith("/"))


def _target_exists(ref: MarkdownLinkRef) -> bool:
    target = _target_without_line_suffix(ref.target)
    return (ref.source.parent / target).resolve().exists()


def _target_files(paths: list[Path]) -> list[Path]:
    if paths:
        files: list[Path] = []
        for path in paths:
            resolved = path.resolve()
            if resolved.is_dir():
                files.extend(sorted(resolved.rglob("*.md")))
            elif resolved.suffix == ".md" and resolved.is_file():
                files.append(resolved)
        return files
    return collect_markdown_files(DOCS)


def _broken_refs(files: list[Path], allowlist: set[str]) -> tuple[list[MarkdownLinkRef], int]:
    broken: list[MarkdownLinkRef] = []
    ignored = 0
    for path in files:
        for ref in extract_markdown_links(path):
            if _target_exists(ref):
                continue
            if _key(ref) in allowlist:
                ignored += 1
                continue
            broken.append(ref)
    return broken, ignored


def _print_broken(refs: list[MarkdownLinkRef], limit: int) -> None:
    shown = refs if limit <= 0 else refs[:limit]
    for ref in shown:
        print(f"M {_rel(ref.source)}:{ref.line}")
        print(f"  markdown: {ref.raw}")
        print(f"  path alvo nao encontrado: {ref.target}")
    hidden = len(refs) - len(shown)
    if hidden > 0:
        print(f"... {hidden} markdown links quebrados omitidos; use --limit 0 para listar tudo.")


def _bucket_for(ref: MarkdownLinkRef) -> str:
    rel = _rel(ref.source)
    if rel in {"docs/BACKLOG.md", "docs/CHANGELOG.md", "docs/DECISIONS.md"}:
        return "docs/shims"
    parts = rel.split("/")
    if len(parts) >= 3 and parts[0] == "docs":
        return "/".join(parts[:2])
    return "outros"


def _print_bucket_summary(refs: list[MarkdownLinkRef]) -> None:
    if not refs:
        return
    print("Por bucket:")
    for bucket, count in sorted(Counter(_bucket_for(ref) for ref in refs).items()):
        print(f"  {bucket}: {count}")


def _target_core_variants(target: str) -> list[str]:
    variants = [target.removeprefix("./")]
    while variants[-1].startswith("../"):
        variants.append(variants[-1][3:])
    if variants[-1].startswith("docs/"):
        variants.append(variants[-1][5:])
    return list(dict.fromkeys(variants))


def _candidate_roots(core: str) -> list[Path]:
    candidates = [REPO_ROOT / core, DOCS / core]
    alias = FIX_ALIASES.get(core)
    if alias is not None:
        candidates.insert(0, alias)
    return candidates


def _normalized_basename(core: str) -> str | None:
    basename = Path(core).name
    if not basename.startswith("track_"):
        return None
    return basename.removeprefix("track_").replace("_", "-")


def _unique_docs_match(filename: str | None) -> Path | None:
    if not filename:
        return None
    matches = list(DOCS.rglob(filename))
    return matches[0].resolve() if len(matches) == 1 else None


def _resolve_fix_candidate(source: Path, target: str) -> Path | None:
    direct = (source.parent / target).resolve()
    if direct.exists():
        return direct
    for core in _target_core_variants(target):
        for candidate in _candidate_roots(core):
            if candidate.exists():
                return candidate.resolve()
        normalized = _unique_docs_match(_normalized_basename(core))
        if normalized is not None:
            return normalized
    return None


def _split_suffixes(target: str) -> tuple[str, str, str]:
    tail_index = min([i for i in [target.find("#"), target.find("?")] if i >= 0] or [len(target)])
    base, tail = target[:tail_index], target[tail_index:]
    line_match = LINE_SUFFIX_RE.search(base)
    if line_match is None:
        return base, "", tail
    return base[: line_match.start()], line_match.group(0), tail


def _relative_target(source: Path, candidate: Path, line_suffix: str, tail: str) -> str:
    rel = os.path.relpath(candidate, start=source.parent)
    return Path(rel).as_posix() + line_suffix + tail


def _fixed_target(source: Path, raw_target: str) -> str | None:
    target = raw_target.strip().strip("<>")
    if not _is_relative_target(target):
        return None
    base, line_suffix, tail = _split_suffixes(target)
    candidate = _resolve_fix_candidate(source, base)
    if candidate is None:
        return None
    fixed = _relative_target(source, candidate, line_suffix, tail)
    return None if fixed == target else fixed


def _fix_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    fixed_count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal fixed_count
        fixed = _fixed_target(path, match.group(2))
        if fixed is None:
            return match.group(0)
        fixed_count += 1
        return f"[{match.group(1)}]({fixed})"

    updated = MARKDOWN_LINK_RE.sub(replace, text)
    if fixed_count:
        path.write_text(updated, encoding="utf-8")
    return fixed_count


def _fix_files(files: list[Path]) -> int:
    return sum(_fix_file(path) for path in files)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Arquivos .md específicos.")
    parser.add_argument("--fix", action="store_true", help="Reescreve links relativos resolvíveis.")
    parser.add_argument("--report", action="store_true", help="Reporta sem falhar.")
    parser.add_argument("--limit", type=int, default=80, help="Máximo de broken links impressos.")
    parser.add_argument("--allowlist", type=Path, default=ALLOWLIST)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    files = _target_files(args.paths)
    if args.fix:
        print(f"Markdown links relativos corrigidos: {_fix_files(files)}.")
    broken, ignored = _broken_refs(files, _load_allowlist(args.allowlist))
    _print_broken(broken, args.limit)
    _print_bucket_summary(broken)
    print(f"Markdown links relativos quebrados: {len(broken)} ({ignored} allowlisted).")
    return 0 if args.report or not broken else 1


if __name__ == "__main__":
    sys.exit(main())
