#!/usr/bin/env python3
"""Atomiza docs/BACKLOG.md em docs/sprint/<X>/lanes/<id>.md (ADR-182, F4.A)."""
# Lê cada `## Sprint <X>` e `### <ID> — <Title>` H3 dentro; gera arquivo
# atômico por lane real com frontmatter conforme docs/_schemas/note-lane.
# Pre-A6 sub-blocos (Bootstrap, 6.5A-F) e utilitários (Lanes abertas,
# Ondas paralelas) vão para docs/sprint/_archive_pre_a6/_README.md.

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _lane_field_extractors import (
    clean_title,
    extract_adrs,
    extract_branch_slug,
    extract_priority,
    extract_ship_date,
    extract_ship_pr,
    extract_status,
    slugify,
)

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "docs" / "BACKLOG.md"
SPRINT_BASE = ROOT / "docs" / "sprint"
ARCHIVE_DIR = SPRINT_BASE / "_archive_pre_a6"

# ----------------------------------------------------------------------
# Regexes de classificação
# ----------------------------------------------------------------------

# Lane ID canônico estendido para casar IDs históricos do BACKLOG.
# Aceita: A10.2, A10.2a, A6e.1, A6e.events, A6e.events-followup,
#         A5f, A6a, A6b.5, A6b.flip, A6-ux.livestep, A6-readers.dbfirst,
#         A6-human, F11.1, F12.8, W1.
LANE_ID_RE = re.compile(r"^[A-Z]\d+[a-z]*(?:-[a-z][a-z0-9-]*)?(?:\.[a-z0-9][a-z0-9-]*)*$")

# Sprint ID: A6, A7, F7, F11, F12.
SPRINT_ID_RE = re.compile(r"^[A-Z]\d+$")

# Heading H3 inicial do lane: `### <ID> — <Title>`. ID vai até o em-dash `—`
# (não usa hyphen como separador — IDs históricos como `A6-ux.livestep` ou
# `A6-human` contêm hyphen interno).
LANE_HEADING_RE = re.compile(r"^### (\S+)\s+—\s+(.+)$")
# Heading auxiliar para blocos pré-A6 com emoji (`### 🛠 Bootstrap ...`).
# Aceita emojis com possível variation selector (️).
PRE_A6_HEADING_RE = re.compile(r"^### ([^\w\s]+(?:️)?)\s+(.+)$")

# Headings utilitários a ignorar (não são lanes mesmo se H3).
UTILITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^Lanes? .* —? ?pickup table"),
    re.compile(r"^Lanes? .* —? ?picklist provisória"),
    re.compile(r"^Lanes A\d+\b", re.IGNORECASE),
    re.compile(r"^Ondas? .* —? ?mapa de dependências"),
    re.compile(r"^Ondas? paralelas"),
    re.compile(r"^Coordenação multi-agente"),
    re.compile(r"^Definition of Done"),
    re.compile(r"^Por que esta sprint existe"),
    re.compile(r"^Lanes abertas agora"),
)

# ----------------------------------------------------------------------
# Modelo
# ----------------------------------------------------------------------


@dataclass
class LaneRecord:
    """Lane atomizada — id, sprint, title, body, frontmatter derivado."""

    raw_id: str
    raw_title: str
    sprint: str
    body_lines: list[str]
    is_active: bool = True
    skip_reason: str = ""
    canonical_id: str = ""
    slug: str = ""
    status: str = "open"
    priority: str | None = None
    branch_slug: str | None = None
    ship_date: str | None = None
    ship_pr: int | None = None
    adrs: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# Parser de BACKLOG.md
# ----------------------------------------------------------------------


def _read_backlog() -> list[str]:
    return BACKLOG.read_text(encoding="utf-8").splitlines()


def _detect_sprint(line: str) -> str | None:
    """Retorna sprint ID se a linha for `## Sprint <X> — ...`; senão None."""
    m = re.match(r"^## Sprint ([A-Z]\d+)\b", line)
    return m.group(1) if m else None


def _detect_phase_header(line: str) -> str | None:
    """Retorna phase ID (`F7`, `F11`, `F12`, `F65`) se H2 for phase header."""
    m = re.match(r"^##\s+(?:\S+\s+)?(F\d+(?:\.\d+)?)\s+", line)
    if not m:
        return None
    return m.group(1).replace(".", "")


def _is_utility_heading(title_after_dash: str, raw_id: str) -> bool:
    """True se o H3 é uma seção utilitária (pickup, ondas, etc.)."""
    candidate = f"{raw_id} {title_after_dash}".strip()
    return any(p.search(candidate) for p in UTILITY_PATTERNS)


def parse_backlog(lines: list[str]) -> list[LaneRecord]:
    """Walk linha-a-linha; emite um LaneRecord por bloco H3 dentro de sprint."""
    state = _ParseState()
    for line in lines:
        _parse_line(line, state)
    state.flush()
    return state.records


@dataclass
class _ParseState:
    """Estado mutável do parser de BACKLOG.md (sprint + lane corrente)."""

    records: list[LaneRecord] = field(default_factory=list)
    current_sprint: str | None = None
    current: LaneRecord | None = None

    def flush(self) -> None:
        if self.current is not None:
            self.records.append(self.current)
            self.current = None


def _parse_line(line: str, state: _ParseState) -> None:
    """Processa 1 linha contra o estado: sprint header, H3 ou body."""
    sprint = _detect_sprint(line) or _detect_phase_header(line)
    if sprint:
        state.flush()
        state.current_sprint = sprint
        return
    if line.startswith("## "):
        state.flush()
        state.current_sprint = None
        return
    if line.startswith("### "):
        state.flush()
        if state.current_sprint is not None:
            state.current = _start_lane(line, state.current_sprint)
        return
    if state.current is not None:
        state.current.body_lines.append(line)


def _start_lane(heading_line: str, sprint: str) -> LaneRecord | None:
    """Detecta H3 do BACKLOG e inicia novo LaneRecord, ou ignora utilitários."""
    pre_a6 = _try_pre_a6_heading(heading_line, sprint)
    if pre_a6 is not None:
        return pre_a6
    m = LANE_HEADING_RE.match(heading_line)
    if not m:
        return None
    raw_id, raw_title = m.group(1).strip(), m.group(2).strip()
    return _classify_lane(raw_id, raw_title, sprint)


def _classify_lane(raw_id: str, raw_title: str, sprint: str) -> LaneRecord | None:
    """Despacha id+title para utility / pre-a6 / lane real / ignore."""
    if _is_utility_heading(raw_title, raw_id):
        return None
    if _looks_pre_a6(raw_id, raw_title):
        return _make_archive_record(raw_id, raw_title, sprint)
    rewritten = ID_REWRITES.get(raw_id, raw_id)
    if not LANE_ID_RE.match(rewritten):
        return None
    return LaneRecord(raw_id=raw_id, raw_title=raw_title, sprint=sprint, body_lines=[])


def _make_archive_record(raw_id: str, raw_title: str, sprint: str) -> LaneRecord:
    return LaneRecord(
        raw_id=raw_id,
        raw_title=raw_title,
        sprint=sprint,
        body_lines=[],
        is_active=False,
        skip_reason="pre-a6 history",
    )


def _try_pre_a6_heading(heading_line: str, sprint: str) -> LaneRecord | None:
    """Captura blocos `### 🛠 Bootstrap ...` e variantes pré-A6 com emoji."""
    m = PRE_A6_HEADING_RE.match(heading_line)
    if not m:
        return None
    return LaneRecord(
        raw_id=m.group(1),
        raw_title=m.group(2).strip(),
        sprint=sprint,
        body_lines=[],
        is_active=False,
        skip_reason="pre-a6 history",
    )


def _looks_pre_a6(raw_id: str, raw_title: str) -> bool:
    """True para Bootstrap, Bloco N, 6.5A-F — pré-Sprint A6 (F6.5)."""
    if raw_id in {"🛠", "🛡", "🛡️", "🧪", "🧩", "🎯", "🔧"}:
        return True
    return bool(re.match(r"^6\.5[A-F]$", raw_id))


# ----------------------------------------------------------------------
# Normalização de lane: id canônico + slug + frontmatter
# ----------------------------------------------------------------------

# Mapping de IDs históricos não-canônicos para o ID canônico desejado.
# IDs canonicais lane-schema-friendly: lowercase pós-ponto/hífen.
ID_REWRITES: dict[str, str] = {
    # F7 phases — IDs `7A`..`7E` viram `F7.a`..`F7.e`; sprint = F7.
    "7A": "F7.a",
    "7B": "F7.b",
    "7C": "F7.c",
    "7D": "F7.d",
    "7E": "F7.e",
    "F7F": "F7.f",
}


def _canonical_id(raw_id: str, sprint: str) -> tuple[str, str]:
    """Retorna (canonical_id, sprint) — aplica rewrites e infere sprint para F7."""
    canonical = ID_REWRITES.get(raw_id, raw_id)
    sprint_final = "F7" if canonical.startswith("F7.") and sprint == "F7" else sprint
    return canonical, sprint_final


def _build_filename(canonical_id: str, slug: str) -> str:
    """Filename = `<id-com-hifen>-<slug>.md`. ID preserva case (matcher do gate)."""
    id_part = canonical_id.replace(".", "-")
    return f"{id_part}-{slug}.md"


# Extração de campos vive em _lane_field_extractors.py (extract_*).


def enrich_lane(record: LaneRecord) -> None:
    """Popula campos derivados do body — status, datas, ADRs, slug etc."""
    body = "\n".join(record.body_lines)
    canonical, sprint_final = _canonical_id(record.raw_id, record.sprint)
    record.canonical_id = canonical
    record.sprint = sprint_final
    record.status = extract_status(body, record.raw_title)
    record.ship_date = extract_ship_date(body, record.raw_title)
    record.ship_pr = extract_ship_pr(body)
    record.branch_slug = extract_branch_slug(body)
    record.adrs = extract_adrs(body)
    record.priority = extract_priority(body, record.raw_title)
    record.raw_title = clean_title(record.raw_title)
    record.slug = slugify(record.raw_title)


# ----------------------------------------------------------------------
# Render frontmatter + escrita
# ----------------------------------------------------------------------


def _yaml_quote(value: str) -> str:
    """Quote seguro para YAML: aspas duplas com escape de aspas internas."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_list(values: list[str]) -> str:
    if not values:
        return "[]"
    items = ", ".join(_yaml_quote(v) for v in values)
    return f"[{items}]"


def _build_tags(record: LaneRecord) -> list[str]:
    """Tags canônicas — type/lane + sprint/<lower> + status/<...> + priority/<lower>."""
    tags = [
        "type/lane",
        f"sprint/{record.sprint.lower()}",
        f"status/{record.status.replace('_', '-')}",
    ]
    if record.priority:
        tags.append(f"priority/{record.priority.lower()}")
    return tags


def render_frontmatter(record: LaneRecord) -> str:
    """Bloco YAML conforme docs/_schemas/note-lane.schema.json."""
    lines = _frontmatter_required(record)
    lines.extend(_frontmatter_optional(record))
    lines.extend(["depends_on: []", "parallel_with: []", "tags:"])
    lines.extend(f"  - {tag}" for tag in _build_tags(record))
    lines.extend(["---", ""])
    return "\n".join(lines) + "\n"


def _frontmatter_required(record: LaneRecord) -> list[str]:
    return [
        "---",
        f"id: {record.canonical_id}",
        "type: lane",
        f"title: {_yaml_quote(record.raw_title)}",
        f"sprint: {record.sprint}",
        f"status: {record.status}",
    ]


def _frontmatter_optional(record: LaneRecord) -> list[str]:
    out: list[str] = []
    if record.priority:
        out.append(f"priority: {record.priority}")
    if record.branch_slug:
        out.append(f"branch_slug: {record.branch_slug}")
    if record.ship_date:
        out.append(f"ship_date: {_yaml_quote(record.ship_date)}")
    if record.ship_pr:
        out.append(f"ship_pr: {record.ship_pr}")
    if record.adrs:
        out.append(f"adrs: {_render_list(record.adrs)}")
    return out


def _strip_trailing_blank(body_lines: list[str]) -> list[str]:
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    return body_lines


def render_body(record: LaneRecord) -> str:
    """Body com H1 (título) + conteúdo preservado do BACKLOG."""
    lines = [f"# {record.raw_id} — {record.raw_title}", ""]
    lines.extend(_strip_trailing_blank(list(record.body_lines)))
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------
# Pre-A6 archive
# ----------------------------------------------------------------------


_ARCHIVE_PREAMBLE = (
    "---\n"
    "id: ARCHIVE-pre-a6\n"
    "type: archive-index\n"
    'title: "Histórico pré-Sprint A6 (F6.5 + Bootstrap blocks)"\n'
    "---\n"
    "\n"
    "# Histórico pré-Sprint A6\n"
    "\n"
    "Blocos H3 do `docs/BACKLOG.md` que precederam o regime de Sprints\n"
    "(Bootstrap + Blocos 1-6 + 6.5A-F). Não são lanes ativas; ficam aqui\n"
    "como histórico de execução para arqueologia.\n"
)


def _build_archive_readme(archived: list[LaneRecord]) -> str:
    """Renderiza docs/sprint/_archive_pre_a6/_README.md com headings históricos."""
    parts = [_ARCHIVE_PREAMBLE]
    parts.extend(_render_archived_block(record) for record in archived)
    return "".join(parts).rstrip() + "\n"


def _render_archived_block(record: LaneRecord) -> str:
    body = "\n".join(_strip_trailing_blank(list(record.body_lines)))
    return f"\n## {record.raw_id} — {record.raw_title}\n\n{body}\n"


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------


def _ensure_dirs(records: list[LaneRecord]) -> None:
    sprints = {r.sprint for r in records if r.is_active}
    for sprint in sorted(sprints):
        (SPRINT_BASE / sprint / "lanes").mkdir(parents=True, exist_ok=True)
    if any(not r.is_active for r in records):
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def write_lane(record: LaneRecord) -> Path:
    """Escreve docs/sprint/<X>/lanes/<id>.md; retorna path."""
    filename = _build_filename(record.canonical_id, record.slug)
    dest = SPRINT_BASE / record.sprint / "lanes" / filename
    payload = render_frontmatter(record) + "\n" + render_body(record)
    dest.write_text(payload, encoding="utf-8")
    return dest


def write_archive(archived: list[LaneRecord]) -> Path | None:
    """Escreve _archive_pre_a6/_README.md se há H3s pré-A6 a preservar."""
    if not archived:
        return None
    dest = ARCHIVE_DIR / "_README.md"
    dest.write_text(_build_archive_readme(archived), encoding="utf-8")
    return dest


def execute(records: list[LaneRecord], *, dry_run: bool) -> tuple[int, int]:
    """Roda enrichment + writes; retorna (lanes, archived)."""
    active = [r for r in records if r.is_active]
    archived = [r for r in records if not r.is_active]
    for record in active:
        enrich_lane(record)
    if dry_run:
        return len(active), len(archived)
    _ensure_dirs(records)
    for record in active:
        write_lane(record)
    write_archive(archived)
    return len(active), len(archived)


def print_summary(records: list[LaneRecord], *, dry_run: bool) -> None:
    """Imprime distribuição por sprint + ids."""
    active = [r for r in records if r.is_active]
    archived = [r for r in records if not r.is_active]
    by_sprint: dict[str, list[LaneRecord]] = {}
    for record in active:
        by_sprint.setdefault(record.sprint, []).append(record)
    print()
    print("Mapping de sprint:")
    for sprint in sorted(by_sprint):
        lanes = sorted(by_sprint[sprint], key=lambda r: r.canonical_id)
        print(f"  {sprint}: {len(lanes)} lanes")
        for lane in lanes:
            tag = " ✅" if lane.status == "shipped" else ""
            print(f"    - {lane.canonical_id} ({lane.status}){tag}")
    print()
    print(f"Total: {len(active)} lanes ativas, {len(archived)} arquivados pré-A6.")
    if dry_run:
        print("(dry-run — nada escrito)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dry-run", action="store_true", help="apenas imprime planejamento")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not BACKLOG.exists():
        print(f"erro: {BACKLOG} não encontrado", file=sys.stderr)
        return 1
    lines = _read_backlog()
    records = parse_backlog(lines)
    if not records:
        print("erro: nenhum H3 lane detectado em BACKLOG.md", file=sys.stderr)
        return 1
    execute(records, dry_run=args.dry_run)
    print_summary(records, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
