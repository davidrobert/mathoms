"""Renderer do CHANGELOG_RECENT.md — janela de 14 dias desde a última entrega (F5.C)."""

# Mantém build_doc_index.py <500 linhas (guideline CLAUDE.md). Recebe notas via
# Protocol estrutural (ChangelogEntryLike) — não importa Note do orquestrador, evita ciclo.
# Spec: docs/plan/DOC_REORG/_README.md §3.4 (frontmatter) + prompt F5.C (formato render).
#
# Determinismo: dias em ordem decrescente (mais recente primeiro), entries dentro
# do dia ordenadas por id ascendente. A janela ancora na data do entry mais
# recente, não no relógio — ver _entry_cutoff().

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Protocol

_CHANGELOG_RECENT_TITLE = "CHANGELOG_RECENT — entregas recentes"
_CHANGELOG_RECENT_FOOTER = ("---", "> Regenerar: `python3 dev/build_doc_index.py --inline`")
_WINDOW_DAYS = 14
_EMPTY_STUB = "_Nenhuma entrega recente registrada como changelog-entry._"
_GENERATED_PATH = (
    Path(__file__).resolve().parent.parent / "docs/_MOC/_generated/CHANGELOG_RECENT.md"
)
_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
_URI_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_LINE_SUFFIX_RE = re.compile(r":\d+(?:-\d+)?$")


class ChangelogEntryLike(Protocol):
    """Duck-type para Note de changelog-entry: campos lidos pelo renderer."""

    path: Path
    id: str
    type: str
    raw: dict[str, Any]


def _is_relative_target(target: str) -> bool:
    if not target or target.startswith("#"):
        return False
    return not (target.startswith("/") or _URI_SCHEME_RE.match(target))


def _split_target(target: str) -> tuple[str, str, str]:
    tail_index = min([i for i in [target.find("#"), target.find("?")] if i >= 0] or [len(target)])
    base, tail = target[:tail_index], target[tail_index:]
    line_match = _LINE_SUFFIX_RE.search(base)
    if line_match is None:
        return base, "", tail
    return base[: line_match.start()], line_match.group(0), tail


def _relative_from_generated(entry_path: Path, target: str) -> str | None:
    base, line_suffix, tail = _split_target(target)
    candidate = (entry_path.parent / base).resolve()
    if not candidate.exists():
        return None
    rel = os.path.relpath(candidate, start=_GENERATED_PATH.parent)
    return Path(rel).as_posix() + line_suffix + tail


def _rewrite_summary_links(summary: str, entry: ChangelogEntryLike) -> str:
    def replace(match: re.Match[str]) -> str:
        target = match.group(2).strip().strip("<>")
        if not _is_relative_target(target):
            return match.group(0)
        fixed = _relative_from_generated(entry.path, target)
        return match.group(0) if fixed is None else f"[{match.group(1)}]({fixed})"

    return _MARKDOWN_LINK_RE.sub(replace, summary)


def _entry_date(entry: ChangelogEntryLike) -> date | None:
    """Lê `date:` do frontmatter e normaliza para `datetime.date`. None se ausente/inválido."""
    raw = entry.raw.get("date")
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _entry_summary_line(entry: ChangelogEntryLike) -> str:
    """Primeira linha não-vazia de `summary:` — usado como rótulo curto da entrada."""
    raw = entry.raw.get("summary")
    if not isinstance(raw, str):
        return entry.id
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped:
            return _rewrite_summary_links(stripped, entry)
    return entry.id


def _entry_lane_wikilink(entry: ChangelogEntryLike) -> str | None:
    """Wikilink da lane (`[[A10.2]]`) se frontmatter tiver. None caso contrário."""
    raw = entry.raw.get("lane")
    if isinstance(raw, str) and raw.startswith("[[") and raw.endswith("]]"):
        return raw
    return None


def _format_entry_line(entry: ChangelogEntryLike) -> str:
    """Bullet de uma entrada: `- [[<id>]] — <resumo>[ (lane <wikilink>)]`."""
    summary = _entry_summary_line(entry)
    lane = _entry_lane_wikilink(entry)
    suffix = f" (lane {lane})" if lane else ""
    return f"- [[{entry.id}]] — {summary}{suffix}"


def _filter_recent(
    entries: list[ChangelogEntryLike],
    cutoff: date,
) -> list[tuple[date, ChangelogEntryLike]]:
    """Pares (date, entry) com `date >= cutoff`. Entries sem data válida são ignoradas."""
    pairs: list[tuple[date, ChangelogEntryLike]] = []
    for entry in entries:
        d = _entry_date(entry)
        if d is None or d < cutoff:
            continue
        pairs.append((d, entry))
    return pairs


def _group_by_day(
    pairs: list[tuple[date, ChangelogEntryLike]],
) -> dict[date, list[ChangelogEntryLike]]:
    """Agrupa entries por dia. Ordem dentro do dia é resolvida no render."""
    by_day: dict[date, list[ChangelogEntryLike]] = {}
    for day, entry in pairs:
        by_day.setdefault(day, []).append(entry)
    return by_day


def _render_day_section(day: date, entries: list[ChangelogEntryLike]) -> list[str]:
    """Bloco h2 do dia + bullets ordenados por id."""
    out: list[str] = [f"## {day.isoformat()} ({len(entries)} entries)", ""]
    for entry in sorted(entries, key=lambda e: e.id):
        out.append(_format_entry_line(entry))
    out.append("")
    return out


# Prefixo de janela desarma o leitor que assume '14 dias corridos a partir de
# hoje' — a âncora é a última entrega registrada, não o relógio.
def _summary_line(pairs: list[tuple[date, ChangelogEntryLike]], anchor: date) -> str:
    """Frase de resumo: janela ancorada + 'N entries entre <data_min> e <data_max>.'."""
    days = [d for d, _ in pairs]
    window = f"Janela de {_WINDOW_DAYS} dias a partir da última entrega registrada ({anchor.isoformat()})."
    return f"{window} {len(pairs)} entries entre {min(days).isoformat()} e {max(days).isoformat()}."


def _render_no_entries(header_fn: Callable[[str], list[str]]) -> list[str]:
    """Vault sem changelog-entries no escopo — stub coerente."""
    lines = header_fn(_CHANGELOG_RECENT_TITLE)
    lines.append(_EMPTY_STUB)
    lines.extend(("", *_CHANGELOG_RECENT_FOOTER))
    return lines


def _dated_pairs(entries: list[ChangelogEntryLike]) -> list[tuple[date, ChangelogEntryLike]]:
    """Pares (date, entry) com data válida no frontmatter. Entries sem data são ignoradas."""
    return [(d, e) for e in entries if (d := _entry_date(e)) is not None]


# Janela ancora na data do entry mais recente (`max(date) - 14d`), não no relógio:
# torna o output função pura das notas versionadas. O gate `doc-index` compara
# commitado vs. regenerado e seria flaky por construção se dependesse de
# `datetime.now()` — a âncora no relógio já causou drift por timezone
# (run 25615590101) e por envelhecimento de branch (PR #543).
def render_changelog_recent(
    entries: list[ChangelogEntryLike],
    header_fn: Callable[[str], list[str]],
) -> list[str]:
    """Monta as linhas do CHANGELOG_RECENT.md — entrypoint do renderer."""
    if not entries:
        return _render_no_entries(header_fn)
    dated = _dated_pairs(entries)
    if not dated:
        return _render_no_entries(header_fn)
    anchor = max(d for d, _ in dated)
    pairs = _filter_recent(entries, anchor - timedelta(days=_WINDOW_DAYS))
    by_day = _group_by_day(pairs)
    lines = header_fn(_CHANGELOG_RECENT_TITLE)
    lines.extend((_summary_line(pairs, anchor), ""))
    for day in sorted(by_day, reverse=True):
        lines.extend(_render_day_section(day, by_day[day]))
    lines.extend(_CHANGELOG_RECENT_FOOTER)
    return lines
