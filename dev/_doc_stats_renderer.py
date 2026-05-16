"""Renderer do DOC_STATS.md - inventario compacto da vault."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Callable, Protocol

_DOC_STATS_TITLE = "DOC_STATS - Inventario da vault"
_DOC_STATS_FOOTER = ("---", "> Regenerar: `python3 dev/build_doc_index.py --inline`")


class NoteLike(Protocol):
    """Duck-type para Note: campos lidos pelo renderer."""

    path: Path
    id: str
    type: str
    status: str
    sprint: str | None
    raw: dict[str, Any]


def _count_by_type(notes: list[NoteLike]) -> Counter[str]:
    return Counter(note.type or "(sem type)" for note in notes)


def _count_by_type_status(notes: list[NoteLike]) -> Counter[tuple[str, str]]:
    return Counter((note.type or "(sem type)", note.status or "(sem status)") for note in notes)


def _render_type_table(notes: list[NoteLike]) -> list[str]:
    out = ["## Por tipo", "", "| type | notas |", "| --- | ---: |"]
    for type_, count in sorted(_count_by_type(notes).items()):
        out.append(f"| {type_} | {count} |")
    out.append("")
    return out


def _render_status_table(notes: list[NoteLike]) -> list[str]:
    out = ["## Por tipo e status", "", "| type | status | notas |", "| --- | --- | ---: |"]
    for (type_, status), count in sorted(_count_by_type_status(notes).items()):
        out.append(f"| {type_} | {status} | {count} |")
    out.append("")
    return out


def _render_sprint_table(notes: list[NoteLike]) -> list[str]:
    sprint_mocs = [
        note for note in notes if note.type == "moc" and str(note.id).startswith("MOC-sprint-")
    ]
    if not sprint_mocs:
        return []
    out = ["## Sprints", "", "| sprint | sprint_status |", "| --- | --- |"]
    for note in sorted(sprint_mocs, key=lambda n: n.id):
        sprint = str(note.id).removeprefix("MOC-sprint-").upper()
        status = str(note.raw.get("sprint_status") or "")
        out.append(f"| {sprint} | {status or '-'} |")
    out.append("")
    return out


def render_doc_stats(
    notes: list[NoteLike],
    header_fn: Callable[[str], list[str]],
) -> list[str]:
    """Monta as linhas do DOC_STATS.md a partir das notas indexadas."""
    lines = header_fn(_DOC_STATS_TITLE)
    lines.extend(("Volta para [`00-INDEX`](../00-INDEX.md).", ""))
    lines.append(f"{len(notes)} notas indexadas pelo frontmatter em `docs/`.")
    lines.append("")
    lines.extend(_render_type_table(notes))
    lines.extend(_render_status_table(notes))
    lines.extend(_render_sprint_table(notes))
    lines.extend(_DOC_STATS_FOOTER)
    return lines
