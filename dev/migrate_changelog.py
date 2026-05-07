#!/usr/bin/env python3
"""Atomiza docs/CHANGELOG.md em docs/sprint/<X>/changelog/<id>.md (ADR-182, F5.A)."""
# Walk linha-a-linha; emite 1 entrada por bullet `^- **...**` (top-level) ou
# por `### YYYY-MM-DD —` heading. Sprint inferido por título strict > body
# heurística > heading-context. Date via regex no título/body, com fallback
# por sprint close-date conhecido. Schema:
# docs/_schemas/note-changelog-entry.schema.json.

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _changelog_field_extractors import (
    derive_scope,
    extract_adrs,
    extract_commits,
    extract_date_from_text,
    extract_lane_ref,
    extract_prs,
    has_breaking,
    infer_sprint_from_full,
    infer_sprint_from_title_strict,
    normalize_sprint,
    sprint_default_date,
)

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "docs" / "CHANGELOG.md"
SPRINT_BASE = ROOT / "docs" / "sprint"
MISC_DIR_NAME = "_misc"

# ----------------------------------------------------------------------
# Regexes de heading + bullet
# ----------------------------------------------------------------------

DATED_H3_RE = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\s+—\s+(.+)$")
PAREN_DATED_H3_RE = re.compile(r"^###\s+(.+?)\s+\((\d{4}-\d{2}-\d{2})\)\s*$")
GENERIC_H3_RE = re.compile(r"^###\s+(.+)$")
PHASE_H2_RE = re.compile(r"^##\s+\[(F\d+(?:\.\d+)?)\]\s+(.+?)\s*$")
GENERIC_H2_RE = re.compile(r"^##\s+(.+)$")
SPRINT_WAVE_H3_RE = re.compile(r"^###\s+Sprint\s+(A\d+)(?:\s+\(.*?\))?\s*$")
TOP_BULLET_RE = re.compile(r"^-\s+\*\*(.+?)\*\*(.*)$")

# H2 títulos que são containers — não viram entries.
H2_CONTAINER_TITLES = ("[Unreleased]", "Versões pré-F0", "Como atualizar este arquivo")


# ----------------------------------------------------------------------
# Modelo
# ----------------------------------------------------------------------


@dataclass
class Entry:
    """Entrada atômica do changelog — id, sprint, title, body, metadados."""

    title: str
    body_lines: list[str] = field(default_factory=list)
    date: str | None = None
    sprint: str | None = None
    lane: str | None = None
    adrs: list[str] = field(default_factory=list)
    prs: list[int] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    breaking: bool = False
    scope: str = ""
    note_id: str = ""


# ----------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------


@dataclass
class _ParseState:
    """Estado mutável do parser linha-a-linha do CHANGELOG."""

    entries: list[Entry] = field(default_factory=list)
    current: Entry | None = None
    sprint_context: str | None = None
    h3_context: str | None = None
    h3_date: str | None = None
    phase_context: str | None = None
    in_phase_entry: bool = False  # True se entry corrente é resumo do `## [FN]`

    def flush(self) -> None:
        if self.current is not None:
            self.entries.append(self.current)
            self.current = None
        self.in_phase_entry = False


def parse_changelog(lines: list[str]) -> list[Entry]:
    """Walk linha-a-linha; emite Entry por top-bullet, dated H3 ou phase H2."""
    state = _ParseState()
    for line in lines:
        _parse_line(line, state)
    state.flush()
    return state.entries


def _parse_line(line: str, state: _ParseState) -> None:
    """Processa 1 linha contra estado: heading, top-bullet ou body."""
    if _handle_heading(line, state):
        return
    if _handle_top_bullet(line, state):
        return
    if state.current is not None:
        state.current.body_lines.append(line)


def _handle_heading(line: str, state: _ParseState) -> bool:
    """True se a linha é um heading (H1/H2/H3)."""
    if line.startswith("# "):
        state.flush()
        return True
    if line.startswith("## "):
        return _handle_h2(line, state)
    if line.startswith("### "):
        return _handle_h3(line, state)
    return False


def _handle_h2(line: str, state: _ParseState) -> bool:
    """H2 phase → entry própria; container → reset; outros → reset."""
    state.flush()
    state.h3_context = None
    state.h3_date = None
    m = PHASE_H2_RE.match(line)
    if m:
        _start_phase_entry(state, m.group(1), m.group(2))
        return True
    state.phase_context = None
    state.sprint_context = None
    return True


def _start_phase_entry(state: _ParseState, phase: str, body_text: str) -> None:
    """Cria entry para `## [FN] Title — date ✅`; marca state.in_phase_entry."""
    state.phase_context = phase
    state.sprint_context = phase
    date = extract_date_from_text(body_text)
    entry = Entry(title=f"[{phase}] {body_text}".strip(), date=date)
    entry.sprint = phase
    state.current = entry
    state.in_phase_entry = True


def _handle_h3(line: str, state: _ParseState) -> bool:
    """H3: Sprint Wave (context only), dated (entry), paren-dated, ou generic."""
    state.flush()
    if _try_sprint_wave(line, state):
        return True
    if _try_dated_h3(line, state):
        return True
    if _try_paren_dated_h3(line, state):
        return True
    if _try_generic_h3(line, state):
        return True
    return False


def _try_sprint_wave(line: str, state: _ParseState) -> bool:
    """`### Sprint A10 (Wave 4)` — só atualiza sprint_context."""
    m = SPRINT_WAVE_H3_RE.match(line)
    if not m:
        return False
    state.sprint_context = m.group(1)
    state.h3_context = None
    state.h3_date = None
    return True


def _try_dated_h3(line: str, state: _ParseState) -> bool:
    """`### 2026-04-25 — Title` — emite entry com date."""
    m = DATED_H3_RE.match(line)
    if not m:
        return False
    date, title = m.group(1), m.group(2).strip()
    _open_h3_entry(state, title=title, date=date)
    return True


def _try_paren_dated_h3(line: str, state: _ParseState) -> bool:
    """`### Title (2026-04-25)` — emite entry com date."""
    m = PAREN_DATED_H3_RE.match(line)
    if not m:
        return False
    title, date = m.group(1).strip(), m.group(2)
    _open_h3_entry(state, title=title, date=date)
    return True


def _try_generic_h3(line: str, state: _ParseState) -> bool:
    """`### Generic Title` — emite entry sem date explícita."""
    m = GENERIC_H3_RE.match(line)
    if not m:
        return False
    title = m.group(1).strip()
    _open_h3_entry(state, title=title, date=extract_date_from_text(title))
    return True


def _open_h3_entry(state: _ParseState, *, title: str, date: str | None) -> None:
    """Abre entry para um H3 (dated ou genérico)."""
    entry = Entry(title=title, date=date)
    entry.sprint = state.sprint_context or _infer_sprint_from_title_loose(title)
    state.current = entry
    state.h3_context = title
    state.h3_date = date


def _infer_sprint_from_title_loose(title: str) -> str | None:
    """Heurística leve para sprint a partir do título (fallback inicial)."""
    m = re.search(r"\b(A\d+|F\d+(?:\.\d+)?|W\d+)\b", title)
    return m.group(1) if m else None


def _handle_top_bullet(line: str, state: _ParseState) -> bool:
    """Top bullet `^- **...**`: nova entry, ou body se em phase/H3 dated."""
    m = TOP_BULLET_RE.match(line)
    if not m:
        return False
    if line.startswith("  ") or line.startswith("\t"):
        return False
    if state.current is not None and (state.in_phase_entry or state.h3_date):
        state.current.body_lines.append(line)
        return True
    _start_bullet_entry(state, line, m)
    return True


def _start_bullet_entry(state: _ParseState, line: str, match: re.Match[str]) -> None:
    """Inicia nova entry a partir de top-bullet."""
    state.flush()
    title_inline = match.group(1).strip()
    rest = match.group(2)
    entry = Entry(title=title_inline)
    entry.body_lines.append(line)
    entry.date = extract_date_from_text(title_inline + " " + rest)
    entry.sprint = state.sprint_context or _infer_sprint_from_title_loose(title_inline)
    state.current = entry


# ----------------------------------------------------------------------
# Enrichment
# ----------------------------------------------------------------------


def enrich_entry(entry: Entry, fallback_date: str) -> None:
    """Popula adrs/prs/commits/breaking + scope/note_id a partir do body."""
    body = "\n".join(entry.body_lines)
    full = f"{entry.title}\n{body}"
    entry.adrs = extract_adrs(full)
    entry.prs = extract_prs(full)
    entry.commits = extract_commits(full)
    entry.breaking = has_breaking(full)
    _resolve_sprint(entry, full)
    _resolve_date(entry, body, fallback_date)
    entry.lane = extract_lane_ref(full)
    entry.scope = derive_scope(
        title=entry.title, lane=entry.lane, prs=entry.prs, sprint=entry.sprint
    )
    entry.note_id = f"CHG-{entry.date}-{entry.scope}"


def _resolve_sprint(entry: Entry, full: str) -> None:
    """Sprint title-strict > body heurística > heading-context (já em entry)."""
    title_sprint = infer_sprint_from_title_strict(entry.title)
    if title_sprint:
        entry.sprint = title_sprint
    elif not entry.sprint:
        entry.sprint = infer_sprint_from_full(full)
    entry.sprint = normalize_sprint(entry.sprint)


def _resolve_date(entry: Entry, body: str, fallback_date: str) -> None:
    """Date: title (já tentado) > body > sprint-default > global fallback."""
    if entry.date:
        return
    entry.date = extract_date_from_text(body) or sprint_default_date(entry.sprint) or fallback_date


# ----------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------


def _yaml_quote(value: str) -> str:
    """Quote seguro para YAML — aspas duplas com escape."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_str_list(values: list[str]) -> str:
    if not values:
        return "[]"
    items = ", ".join(_yaml_quote(v) for v in values)
    return f"[{items}]"


def _render_int_list(values: list[int]) -> str:
    return "[" + ", ".join(str(v) for v in values) + "]" if values else "[]"


def _build_tags(entry: Entry) -> list[str]:
    """Tags: type/changelog-entry + sprint/<lc> + breaking/yes (se aplicável)."""
    tags = ["type/changelog-entry"]
    if entry.sprint:
        tags.append(f"sprint/{entry.sprint.lower()}")
    if entry.breaking:
        tags.append("breaking/yes")
    return tags


def _summary_from_body(entry: Entry) -> str:
    """Título + 1ª frase do body, ≤ 600 chars."""
    title = entry.title.strip().rstrip(":")
    body_text = " ".join(line.strip() for line in entry.body_lines if line.strip())
    body_text = re.sub(r"\s+", " ", body_text)
    snippet = ""
    if body_text:
        m = re.match(r"^.{40,200}?[.](?=\s|$)", body_text)
        snippet = (m.group(0) if m else body_text[:160]).strip()
    summary = f"{title}. {snippet}".strip()
    return summary[:597] + "..." if len(summary) > 600 else summary


def render_frontmatter(entry: Entry) -> str:
    """Bloco YAML conforme docs/_schemas/note-changelog-entry.schema.json."""
    lines = _frontmatter_required(entry)
    lines.extend(_frontmatter_optional(entry))
    lines.extend(_frontmatter_summary(entry))
    lines.append("tags:")
    lines.extend(f"  - {tag}" for tag in _build_tags(entry))
    lines.extend(["---", ""])
    return "\n".join(lines) + "\n"


def _frontmatter_required(entry: Entry) -> list[str]:
    out = [
        "---",
        f"id: {entry.note_id}",
        "type: changelog-entry",
        f"date: {_yaml_quote(entry.date)}",
    ]
    out.append(f"sprint: {entry.sprint}" if entry.sprint else "sprint: null")
    return out


def _frontmatter_optional(entry: Entry) -> list[str]:
    out: list[str] = []
    if entry.lane:
        out.append(f"lane: {_yaml_quote(entry.lane)}")
    if entry.adrs:
        out.append(f"adrs: {_render_str_list(entry.adrs)}")
    if entry.prs:
        out.append(f"prs: {_render_int_list(entry.prs)}")
    if entry.commits:
        out.append(f"commits: {_render_str_list(entry.commits)}")
    if entry.breaking:
        out.append("breaking: true")
    return out


def _frontmatter_summary(entry: Entry) -> list[str]:
    summary = _summary_from_body(entry)
    if "\n" in summary or len(summary) > 200:
        out = ["summary: |"]
        out.extend(f"  {sline}" for sline in summary.splitlines() or [summary])
        return out
    return [f"summary: {_yaml_quote(summary)}"]


def _strip_trailing_blank(body_lines: list[str]) -> list[str]:
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    return body_lines


def render_body(entry: Entry) -> str:
    """Body com H1 (título) + conteúdo preservado do CHANGELOG."""
    title = entry.title.strip().rstrip(":")
    lines = [f"# {title}", ""]
    lines.extend(_strip_trailing_blank(list(entry.body_lines)))
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------
# IO
# ----------------------------------------------------------------------


def _ensure_dir(entry: Entry) -> Path:
    """Cria/retorna docs/sprint/<X>/changelog/."""
    sprint = entry.sprint or MISC_DIR_NAME
    dest = SPRINT_BASE / sprint / "changelog"
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def write_entry(entry: Entry) -> Path:
    """Escreve docs/sprint/<X>/changelog/<id>.md."""
    dest = _ensure_dir(entry) / f"{entry.note_id}.md"
    payload = render_frontmatter(entry) + "\n" + render_body(entry)
    dest.write_text(payload, encoding="utf-8")
    return dest


def _dedupe_ids(entries: list[Entry]) -> None:
    """Resolve colisões appendando `-<n>` em ordem de aparição."""
    seen: dict[str, int] = {}
    for entry in entries:
        base = entry.note_id
        if base in seen:
            seen[base] += 1
            entry.note_id = f"{base}-{seen[base]}"
        else:
            seen[base] = 0


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------


def execute(entries: list[Entry], *, dry_run: bool) -> int:
    """Escreve entries; retorna count escrito (ou planejado em dry-run)."""
    if dry_run:
        return len(entries)
    for entry in entries:
        write_entry(entry)
    return len(entries)


def print_summary(entries: list[Entry], *, dry_run: bool) -> None:
    """Distribuição por sprint + estatísticas globais."""
    by_sprint = _group_by_sprint(entries)
    print()
    print(f"Total: {len(entries)} entradas atomizadas")
    for sprint in sorted(by_sprint):
        print(f"  {sprint}: {len(by_sprint[sprint])} entradas")
    total_adrs = sum(len(e.adrs) for e in entries)
    total_prs = sum(len(e.prs) for e in entries)
    total_commits = sum(len(e.commits) for e in entries)
    print(f"Refs agregadas: {total_adrs} ADRs, {total_prs} PRs, {total_commits} commits")
    if dry_run:
        print("(dry-run — nada escrito)")


def _group_by_sprint(entries: list[Entry]) -> dict[str, list[Entry]]:
    out: dict[str, list[Entry]] = {}
    for entry in entries:
        out.setdefault(entry.sprint or MISC_DIR_NAME, []).append(entry)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dry-run", action="store_true", help="apenas planeja, não escreve")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not CHANGELOG.exists():
        print(f"erro: {CHANGELOG} não encontrado", file=sys.stderr)
        return 1
    lines = CHANGELOG.read_text(encoding="utf-8").splitlines()
    entries = parse_changelog(lines)
    if not entries:
        print("erro: nenhuma entrada detectada em CHANGELOG.md", file=sys.stderr)
        return 1
    fallback_date = "2026-04-15"
    for entry in entries:
        enrich_entry(entry, fallback_date)
    _dedupe_ids(entries)
    execute(entries, dry_run=args.dry_run)
    print_summary(entries, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
