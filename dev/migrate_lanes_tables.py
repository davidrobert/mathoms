#!/usr/bin/env python3
"""Atomiza lanes de tabelas markdown em A7-A11 do BACKLOG arquivado (ADR-182, F4.A.followup)."""
# F4.A migrou apenas H3 lanes; ~39 lanes vivem em tabelas dentro de seções
# `## Sprint A7..A11` e ficaram fora. Este script lê o backup
# `docs/archive/BACKLOG-pre-shim-2026-05-07.md`, encontra cada tabela
# imediatamente após `### Lanes A<N>` e gera arquivo atômico por linha.
# Idempotente: pula lanes cujo destino já existe.

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
    slugify,
)
from _lane_table_parsers import (
    TABLE_ROW_RE,
    build_filename,
    canonicalize,
    extract_id_and_title,
    has_lane_column,
    is_lane_row,
    qualify_id,
    skip_separator,
    split_row,
)

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_BACKLOG = ROOT / "docs" / "archive" / "BACKLOG-pre-shim-2026-05-07.md"
SPRINT_BASE = ROOT / "docs" / "sprint"

# Sprints alvo: tabelas A7-A11 ficaram fora da F4.A inicial (apenas H3 lanes).
TARGET_SPRINTS: tuple[str, ...] = ("A7", "A8", "A9", "A10", "A11")

SPRINT_HEADER_RE = re.compile(r"^## Sprint (A\d+)\b")


@dataclass
class TableLane:
    """Lane extraída de uma linha de tabela markdown."""

    raw_id: str
    sprint: str
    raw_title: str
    cells: dict[str, str]
    body_blob: str
    canonical_id: str = ""
    alias_id: str | None = None
    slug: str = ""
    title: str = ""
    status: str = "open"
    priority: str | None = None
    branch_slug: str | None = None
    ship_date: str | None = None
    ship_pr: int | None = None
    adrs: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# Parser de tabelas — encontra `### Lanes <X>` + tabela seguinte
# ----------------------------------------------------------------------


def _read_archive() -> list[str]:
    if not ARCHIVE_BACKLOG.exists():
        raise FileNotFoundError(f"{ARCHIVE_BACKLOG} não encontrado")
    return ARCHIVE_BACKLOG.read_text(encoding="utf-8").splitlines()


def _build_table_lane(headers: list[str], cells: list[str], sprint: str) -> TableLane | None:
    """Mapeia células ao header e produz TableLane se id válido."""
    if len(cells) != len(headers):
        # Tabelas mal-formadas (escape de `|` interno em link) — ignora.
        return None
    cell_map = dict(zip(headers, cells))
    lane_cell = cell_map.get("Lane") or cell_map.get("Wave") or ""
    parsed = extract_id_and_title(lane_cell)
    if parsed is None:
        return None
    raw_id, raw_title = parsed
    return TableLane(
        raw_id=qualify_id(raw_id, sprint),
        sprint=sprint,
        raw_title=raw_title,
        cells=cell_map,
        body_blob="\n".join(cells),
    )


def _try_emit_lane(line: str, headers: list[str], sprint: str, sink: list[TableLane]) -> None:
    """Se a linha é lane row, constrói TableLane e adiciona ao sink."""
    cells = split_row(line)
    if not is_lane_row(cells):
        return
    lane = _build_table_lane(headers, cells, sprint)
    if lane is not None:
        sink.append(lane)


def _collect_table_rows(
    lines: list[str], cursor: int, headers: list[str], sprint: str
) -> tuple[list[TableLane], int]:
    """Itera linhas de tabela emitindo lanes; pára na primeira linha não-row."""
    out: list[TableLane] = []
    while cursor < len(lines) and TABLE_ROW_RE.match(lines[cursor]):
        _try_emit_lane(lines[cursor], headers, sprint, out)
        cursor += 1
    return out, cursor


def _parse_table_block(lines: list[str], start: int, sprint: str) -> tuple[list[TableLane], int]:
    """Lê tabela a partir de `lines[start]` (header `|...|`). Retorna (lanes, next_idx)."""
    headers = split_row(lines[start])
    if not has_lane_column(headers):
        return [], start + 1
    cursor = skip_separator(lines, start + 1)
    return _collect_table_rows(lines, cursor, headers, sprint)


def _resolve_sprint_at_h2(line: str) -> str | None:
    """Aplica reset de sprint em qualquer H2; re-arma se Sprint A7..A11."""
    sprint_match = SPRINT_HEADER_RE.match(line)
    if sprint_match and sprint_match.group(1) in TARGET_SPRINTS:
        return sprint_match.group(1)
    return None


def parse_archive_tables() -> list[TableLane]:
    """Walk o arquivo arquivado; coleta lanes de cada tabela em sprint A7-A11."""
    lines = _read_archive()
    lanes: list[TableLane] = []
    current_sprint: str | None = None
    cursor = 0
    while cursor < len(lines):
        line = lines[cursor]
        if line.startswith("## "):
            current_sprint = _resolve_sprint_at_h2(line)
            cursor += 1
            continue
        if current_sprint and TABLE_ROW_RE.match(line):
            block, cursor = _parse_table_block(lines, cursor, current_sprint)
            lanes.extend(block)
            continue
        cursor += 1
    return lanes


# ----------------------------------------------------------------------
# Normalização de status / campos derivados
# ----------------------------------------------------------------------


def _is_shipped_marker(text: str, lowered: str) -> bool:
    return "✅" in text or "shipped" in lowered or "entregue" in lowered or "mergeado" in lowered


def _is_in_progress_marker(text: str, lowered: str) -> bool:
    if "🚧" in text:
        return True
    return any(needle in lowered for needle in ("in_progress", "in-progress", "wip", "em revis"))


def _normalize_status(text: str) -> str:
    """Detecta status no texto livre; default open."""
    lowered = text.lower()
    if _is_shipped_marker(text, lowered):
        return "shipped"
    if "❌" in text or "cancel" in lowered or "descartad" in lowered:
        return "cancelled"
    if _is_in_progress_marker(text, lowered):
        return "in_progress"
    if "⏸" in text or "blocked" in lowered:
        return "blocked"
    if "ready" in lowered:
        return "open"
    if "planned" in lowered or "planejad" in lowered or "☐" in text:
        return "planned"
    return "open"


def _resolve_status_field(lane: TableLane) -> str:
    """Status vem da célula `Status` apenas — body_blob inclui dependências (`✅`
    em coluna Depende-de não significa shipped da lane)."""
    status_cell = lane.cells.get("Status") or lane.cells.get("Tasks") or ""
    if not status_cell.strip():
        return _normalize_status(lane.body_blob)
    return _normalize_status(status_cell)


def _resolve_branch_slug(lane: TableLane) -> str | None:
    """Branch slug: célula `Branch slug` (com backticks) ou regex no body."""
    cell = lane.cells.get("Branch slug") or ""
    m = re.search(r"`([a-z0-9][a-z0-9-]*)`", cell)
    if m:
        return m.group(1)
    return extract_branch_slug(lane.body_blob)


def _resolve_pr(lane: TableLane) -> int | None:
    """PR: célula `PR` (numero ou link `[#NN]`) ou regex no body."""
    cell = lane.cells.get("PR") or ""
    if cell.strip().isdigit():
        return int(cell.strip())
    m = re.search(r"#(\d{2,5})", cell)
    if m:
        return int(m.group(1))
    return extract_ship_pr(lane.body_blob)


def _resolve_ship_date(lane: TableLane) -> str | None:
    cell = lane.cells.get("Ship date") or ""
    m = re.match(r"\d{4}-\d{2}-\d{2}", cell.strip())
    if m:
        return m.group(0)
    return extract_ship_date(lane.body_blob, lane.raw_title)


def enrich_lane(lane: TableLane) -> None:
    """Popula campos derivados — id canônico, slug, frontmatter."""
    canonical, alias = canonicalize(lane.raw_id)
    lane.canonical_id = canonical
    lane.alias_id = alias
    lane.title = clean_title(lane.raw_title)
    lane.slug = slugify(lane.title)
    lane.status = _resolve_status_field(lane)
    lane.priority = extract_priority(lane.body_blob, lane.raw_title)
    lane.branch_slug = _resolve_branch_slug(lane)
    lane.ship_date = _resolve_ship_date(lane)
    lane.ship_pr = _resolve_pr(lane)
    lane.adrs = extract_adrs(lane.body_blob)


# ----------------------------------------------------------------------
# Render frontmatter + escrita
# ----------------------------------------------------------------------


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return f"[{', '.join(_yaml_quote(v) for v in values)}]"


def _build_tags(lane: TableLane) -> list[str]:
    tags = [
        "type/lane",
        f"sprint/{lane.sprint.lower()}",
        f"status/{lane.status.replace('_', '-')}",
    ]
    if lane.priority:
        tags.append(f"priority/{lane.priority.lower()}")
    return tags


def _frontmatter_required(lane: TableLane) -> list[str]:
    return [
        "---",
        f"id: {lane.canonical_id}",
        "type: lane",
        f"title: {_yaml_quote(lane.title)}",
        f"sprint: {lane.sprint}",
        f"status: {lane.status}",
    ]


def _frontmatter_optional(lane: TableLane) -> list[str]:
    out: list[str] = []
    if lane.alias_id:
        out.append(f"aliases: {_render_list([lane.alias_id])}")
    if lane.priority:
        out.append(f"priority: {lane.priority}")
    if lane.branch_slug:
        out.append(f"branch_slug: {lane.branch_slug}")
    if lane.ship_date:
        out.append(f"ship_date: {_yaml_quote(lane.ship_date)}")
    if lane.ship_pr:
        out.append(f"ship_pr: {lane.ship_pr}")
    if lane.adrs:
        out.append(f"adrs: {_render_list(lane.adrs)}")
    return out


def render_frontmatter(lane: TableLane) -> str:
    lines = _frontmatter_required(lane)
    lines.extend(_frontmatter_optional(lane))
    lines.extend(["depends_on: []", "parallel_with: []", "tags:"])
    lines.extend(f"  - {tag}" for tag in _build_tags(lane))
    lines.extend(["---", ""])
    return "\n".join(lines) + "\n"


def _render_metadata_section(lane: TableLane) -> list[str]:
    """Bloco com colunas custom da tabela original (Onda, Depende de, etc.)."""
    interesting = ("Onda", "Depende de", "Plano", "Branch slug", "Esforço", "Tasks", "Paralelo com")
    rows = [(k, lane.cells.get(k, "").strip()) for k in interesting if lane.cells.get(k)]
    if not rows:
        return []
    out = ["## Contexto da tabela original", ""]
    out.extend(f"- **{key}:** {value}" for key, value in rows)
    out.append("")
    return out


def _render_status_section(lane: TableLane) -> list[str]:
    cell = lane.cells.get("Status") or lane.cells.get("Tasks")
    if not cell:
        return []
    return ["## Status (legado)", "", cell, ""]


def render_body(lane: TableLane) -> str:
    """Body sintético — célula `Status` preservada + nota de migração."""
    parts = [
        f"# {lane.canonical_id} — {lane.title}",
        "",
        f"> Migrada de tabela em `## Sprint {lane.sprint}` do BACKLOG (F4.A.followup, ADR-182).",
        "",
    ]
    parts.extend(_render_metadata_section(lane))
    parts.extend(_render_status_section(lane))
    return "\n".join(parts) + "\n"


# ----------------------------------------------------------------------
# Driver — escrita de lanes + atualização de editorial
# ----------------------------------------------------------------------


def _ensure_dirs(lanes: list[TableLane]) -> None:
    for sprint in {lane.sprint for lane in lanes}:
        (SPRINT_BASE / sprint / "lanes").mkdir(parents=True, exist_ok=True)


def _target_path(lane: TableLane) -> Path:
    return SPRINT_BASE / lane.sprint / "lanes" / build_filename(lane.canonical_id, lane.slug)


def _write_lane(lane: TableLane) -> Path:
    dest = _target_path(lane)
    payload = render_frontmatter(lane) + "\n" + render_body(lane)
    dest.write_text(payload, encoding="utf-8")
    return dest


def _count_targets(lanes: list[TableLane]) -> tuple[int, int]:
    """Conta destinos novos vs já-existentes (sem escrever)."""
    written = sum(1 for lane in lanes if not _target_path(lane).exists())
    skipped = len(lanes) - written
    return written, skipped


def _write_new_lanes(lanes: list[TableLane]) -> tuple[int, int]:
    """Escreve só lanes cujo destino não existe; retorna (escritas, puladas)."""
    written = 0
    skipped = 0
    for lane in lanes:
        if _target_path(lane).exists():
            skipped += 1
            continue
        _write_lane(lane)
        written += 1
    return written, skipped


def execute(lanes: list[TableLane], *, dry_run: bool) -> tuple[int, int]:
    """Roda enrich + writes pulando lanes cujo destino já existe."""
    for lane in lanes:
        enrich_lane(lane)
    if dry_run:
        return _count_targets(lanes)
    _ensure_dirs(lanes)
    return _write_new_lanes(lanes)


# ----------------------------------------------------------------------
# Editorial lanes.md — reescrita de wikilinks alias → canonical
# ----------------------------------------------------------------------


def _group_by_sprint(lanes: list[TableLane]) -> dict[str, list[TableLane]]:
    """Apenas lanes com alias precisam reescrita no editorial."""
    out: dict[str, list[TableLane]] = {}
    for lane in lanes:
        if lane.alias_id is None:
            continue
        out.setdefault(lane.sprint, []).append(lane)
    return out


def _rewrite_editorial(text: str, sprint_lanes: list[TableLane]) -> tuple[str, int]:
    """Aplica replace `[[alias]]` → `[[canonical]]`; retorna (texto novo, total replaces)."""
    replacements = 0
    for lane in sprint_lanes:
        needle = f"[[{lane.alias_id}]]"
        count = text.count(needle)
        if count:
            text = text.replace(needle, f"[[{lane.canonical_id}]]")
            replacements += count
    return text, replacements


def update_editorial_lanes_md(lanes: list[TableLane], *, dry_run: bool) -> dict[str, int]:
    """Renomeia wikilinks `[[<alias>]]` em `docs/sprint/<X>/lanes.md` para canonical."""
    summary: dict[str, int] = {}
    for sprint, sprint_lanes in _group_by_sprint(lanes).items():
        editorial = SPRINT_BASE / sprint / "lanes.md"
        if not editorial.exists():
            continue
        text = editorial.read_text(encoding="utf-8")
        new_text, replacements = _rewrite_editorial(text, sprint_lanes)
        if replacements == 0:
            continue
        summary[str(editorial.relative_to(ROOT))] = replacements
        if not dry_run:
            editorial.write_text(new_text, encoding="utf-8")
    return summary


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def _format_lane_line(lane: TableLane) -> str:
    alias_note = f" (alias: {lane.alias_id})" if lane.alias_id else ""
    tag = " ✅" if lane.status == "shipped" else ""
    return f"    - {lane.canonical_id} ({lane.status}){alias_note}{tag}"


def print_summary(lanes: list[TableLane], written: int, skipped: int) -> None:
    by_sprint: dict[str, list[TableLane]] = {}
    for lane in lanes:
        by_sprint.setdefault(lane.sprint, []).append(lane)
    print()
    print("Lanes detectadas em tabelas:")
    for sprint in sorted(by_sprint):
        sprint_lanes = sorted(by_sprint[sprint], key=lambda lane: lane.canonical_id)
        print(f"  {sprint}: {len(sprint_lanes)} lanes")
        for lane in sprint_lanes:
            print(_format_lane_line(lane))
    print()
    print(f"Total: {written} escritas, {skipped} puladas (já existem).")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dry-run", action="store_true", help="apenas imprime planejamento")
    return parser.parse_args()


def _print_editorial_summary(edits: dict[str, int]) -> None:
    if not edits:
        return
    print()
    print("Editoriais atualizados:")
    for path, count in edits.items():
        print(f"  {path}: {count} wikilinks reescritos")


def main() -> int:
    args = parse_args()
    if not ARCHIVE_BACKLOG.exists():
        print(f"erro: {ARCHIVE_BACKLOG} não encontrado", file=sys.stderr)
        return 1
    lanes = parse_archive_tables()
    if not lanes:
        print("erro: nenhuma lane detectada em tabelas A7-A11", file=sys.stderr)
        return 1
    written, skipped = execute(lanes, dry_run=args.dry_run)
    edits = update_editorial_lanes_md(lanes, dry_run=args.dry_run)
    print_summary(lanes, written, skipped)
    _print_editorial_summary(edits)
    if args.dry_run:
        print("(dry-run — nada escrito)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
