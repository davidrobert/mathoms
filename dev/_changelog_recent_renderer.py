"""Renderer do CHANGELOG_RECENT.md — entries dos últimos 14 dias agregados por dia (F5.C)."""

# Mantém build_doc_index.py <500 linhas (guideline CLAUDE.md). Recebe notas via
# Protocol estrutural (ChangelogEntryLike) — não importa Note do orquestrador, evita ciclo.
# Spec: docs/plan/DOC_REORG/_README.md §3.4 (frontmatter) + prompt F5.C (formato render).
#
# Determinismo: dias em ordem decrescente (mais recente primeiro), entries dentro
# do dia ordenadas por id ascendente. `today_fn` é injetável para smoke tests.

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

_CHANGELOG_RECENT_TITLE = "CHANGELOG_RECENT — últimos 14 dias"
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


def _summary_line(pairs: list[tuple[date, ChangelogEntryLike]]) -> str:
    """Frase 'N entries entre <data_min> e <data_max>.' a partir dos pares filtrados."""
    days = [d for d, _ in pairs]
    return f"{len(pairs)} entries entre {min(days).isoformat()} e {max(days).isoformat()}."


def _render_no_entries(header_fn: Callable[[str], list[str]]) -> list[str]:
    """Vault sem changelog-entries no escopo — stub coerente."""
    lines = header_fn(_CHANGELOG_RECENT_TITLE)
    lines.append(_EMPTY_STUB)
    lines.extend(("", *_CHANGELOG_RECENT_FOOTER))
    return lines


def _today_utc() -> date:
    """Data corrente em UTC — runner CI vs. dev local (BRT) divergiam ao
    redor da meia-noite UTC, causando drift recorrente em
    `CHANGELOG_RECENT.md` (run [25615590101](https://github.com/davidrobert/mathoms/actions/runs/25615590101))."""
    return datetime.now(timezone.utc).date()


def render_changelog_recent(
    entries: list[ChangelogEntryLike],
    header_fn: Callable[[str], list[str]],
    today_fn: Callable[[], date] = _today_utc,
) -> list[str]:
    """Monta as linhas do CHANGELOG_RECENT.md — entrypoint do renderer."""
    if not entries:
        return _render_no_entries(header_fn)
    cutoff = today_fn() - timedelta(days=_WINDOW_DAYS)
    pairs = _filter_recent(entries, cutoff)
    if not pairs:
        return _render_no_entries(header_fn)
    by_day = _group_by_day(pairs)
    lines = header_fn(_CHANGELOG_RECENT_TITLE)
    lines.extend((_summary_line(pairs), ""))
    for day in sorted(by_day, reverse=True):
        lines.extend(_render_day_section(day, by_day[day]))
    lines.extend(_CHANGELOG_RECENT_FOOTER)
    return lines
