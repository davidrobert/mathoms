"""Renderer do SPRINT_CURRENT.md — lanes da sprint corrente filtradas por status (F4.C)."""

# Mantém build_doc_index.py <500 linhas (guideline CLAUDE.md). Recebe notas via
# Protocol estrutural (LaneLike) — não importa Note do orquestrador, evita ciclo.
# Spec: docs/plan/DOC_REORG/_README.md §6.4 (Fase 4, item C).
#
# Detecção de sprint corrente: prioridade por letra (A > F > W), maior número.
# Sprints "A" são oficiais; "F" são fases legadas; "W" são ondas dentro de uma
# sprint "A" — só contam como corrente se nenhuma "A" existir. Quando A11 é
# corrente, lanes com sprint W5/W6 são agregadas (waves pertencem a A11).

from __future__ import annotations

from typing import Any, Callable, Protocol

_SPRINT_CURRENT_TITLE = "SPRINT_CURRENT — Lanes da sprint corrente"
_SPRINT_CURRENT_FOOTER = ("---", "> Regenerar: `python3 dev/build_doc_index.py --inline`")

# Status de lane que contam como "prontos para pickup" / "em execução".
# `consumed` é status de TRACK (não lane) e nunca aparece aqui.
LANE_STATUS_OPEN: frozenset[str] = frozenset({"ready", "open", "in_progress"})
_STATUS_DISPLAY_ORDER: tuple[str, ...] = ("ready", "open", "in_progress")
_STATUS_HEADINGS: dict[str, str] = {
    "ready": "Ready",
    "open": "Open",
    "in_progress": "In progress",
}

# Prioridade de detecção de sprint corrente. "A" (sprint oficial) ganha de "F"
# (fase legada) que ganha de "W" (onda dentro de A). Outras letras caem por
# último em ordem alfabética.
_LETTER_PRIORITY: dict[str, int] = {"A": 3, "F": 2, "W": 1}

# Mapa de ondas → sprint pai. Quando A11 é corrente, lanes com sprint W5/W6
# também contam. Atualize quando novas ondas surgirem (idealmente, quando F4.A
# popular lanes, o frontmatter delas usa `sprint: A11` direto e este mapa
# pode encolher).
_WAVE_PARENT: dict[str, str] = {"W5": "A11", "W6": "A11"}


class LaneLike(Protocol):
    """Duck-type para Note de lane: campos lidos pelo renderer."""

    id: str
    title: str
    status: str
    sprint: str | None
    raw: dict[str, Any]


def _sprint_priority_key(sprint_id: str) -> tuple[int, int, str]:
    """Chave de ordenação (peso letra A>F>W, número, id) — maior vence."""
    if not sprint_id:
        return (0, 0, "")
    letter = sprint_id[0]
    try:
        number = int(sprint_id[1:])
    except ValueError:
        number = 0
    weight = _LETTER_PRIORITY.get(letter, 0)
    return (weight, number, sprint_id)


def _eligible_sprints(candidates: set[str]) -> set[str]:
    """Remove waves cujo pai (sprint A) também está em candidates — wave perde para o pai."""
    parents_present = {p for _w, p in _WAVE_PARENT.items() if p in candidates}
    eligible = {
        s for s in candidates if s not in _WAVE_PARENT or _WAVE_PARENT[s] not in parents_present
    }
    return eligible or candidates


def _detect_current_sprint(lanes: list[LaneLike], available_sprints: set[str]) -> str | None:
    """Sprint corrente: max(A>F>W, número) entre `available_sprints` ou inferido das lanes."""
    candidates = available_sprints or {lane.sprint for lane in lanes if lane.sprint}
    if not candidates:
        return None
    return max(_eligible_sprints(candidates), key=_sprint_priority_key)


def _expand_sprint_aliases(current: str) -> set[str]:
    """Sprint corrente + ondas que pertencem a ela. Ex.: A11 → {A11, W5, W6}."""
    aliases = {current}
    aliases.update(w for w, parent in _WAVE_PARENT.items() if parent == current)
    return aliases


def _filter_sprint_lanes(lanes: list[LaneLike], current: str) -> list[LaneLike]:
    """Lanes cuja sprint é a corrente OU uma onda da corrente."""
    aliases = _expand_sprint_aliases(current)
    return [lane for lane in lanes if lane.sprint in aliases]


def _bucket_lanes_by_status(lanes: list[LaneLike]) -> dict[str, list[LaneLike]]:
    """Agrupa lanes por status canônico. Ignora status fora de LANE_STATUS_OPEN."""
    by_status: dict[str, list[LaneLike]] = {s: [] for s in _STATUS_DISPLAY_ORDER}
    for lane in lanes:
        if lane.status in LANE_STATUS_OPEN:
            by_status.setdefault(lane.status, []).append(lane)
    return by_status


def _summary_line(by_status: dict[str, list[LaneLike]]) -> str:
    """Frase 'N ready · M in_progress · K open' (omite zeros)."""
    parts: list[str] = []
    for status in _STATUS_DISPLAY_ORDER:
        count = len(by_status.get(status, []))
        if count:
            parts.append(f"{count} {status}")
    if not parts:
        return "Nenhuma lane prontidão atual."
    return " · ".join(parts) + "."


def _format_lane_line(lane: LaneLike) -> str:
    """Linha por lane: wikilink + título + priority + branch_slug (se houver)."""
    extras: list[str] = []
    priority = lane.raw.get("priority")
    if priority not in (None, ""):
        extras.append(f"priority {priority}")
    branch_slug = lane.raw.get("branch_slug")
    if branch_slug not in (None, ""):
        extras.append(f"branch `{branch_slug}`")
    suffix = f" · {' · '.join(extras)}" if extras else ""
    title = lane.title or lane.id
    return f"- [[{lane.id}]] — {title}{suffix}"


def _lane_sort_key(lane: LaneLike) -> str:
    """Ordena lanes por id ascendente (estável dentro do bucket de status)."""
    return lane.id


def _render_status_section(status: str, bucket: list[LaneLike]) -> list[str]:
    """Renderiza um h2 de status + bullets de lanes ordenadas por id."""
    heading = _STATUS_HEADINGS.get(status, status)
    out: list[str] = [f"## {heading} ({len(bucket)})", ""]
    for lane in sorted(bucket, key=_lane_sort_key):
        out.append(_format_lane_line(lane))
    out.append("")
    return out


def _render_inspection_listing(sprint_lanes: list[LaneLike]) -> list[str]:
    """Quando ready/open/in_progress está vazio: lista todas as lanes para inspeção."""
    out: list[str] = ["## Todas as lanes da sprint (para inspeção)", ""]
    by_status: dict[str, list[LaneLike]] = {}
    for lane in sprint_lanes:
        by_status.setdefault(lane.status or "(sem status)", []).append(lane)
    for status in sorted(by_status):
        bucket = sorted(by_status[status], key=_lane_sort_key)
        out.append(f"### {status} ({len(bucket)})")
        out.append("")
        for lane in bucket:
            out.append(_format_lane_line(lane))
        out.append("")
    return out


def _render_no_sprint(header_fn: Callable[[str], list[str]]) -> list[str]:
    """Vault sem sprints indexadas — stub."""
    lines = header_fn(_SPRINT_CURRENT_TITLE)
    lines.extend(("Volta para [`00-INDEX`](../00-INDEX.md).", ""))
    lines.append(
        "_Nenhuma lane atomizada ainda — Fase 4 do DOC_REORG popula `docs/sprint/<X>/lanes/`._"
    )
    lines.extend(("", *_SPRINT_CURRENT_FOOTER))
    return lines


def _render_no_lanes_in_sprint(header_fn: Callable[[str], list[str]], current: str) -> list[str]:
    """Sprint corrente detectada, mas sem lanes com frontmatter ainda."""
    lines = header_fn(f"{_SPRINT_CURRENT_TITLE} — {current}")
    lines.extend(("Volta para [`00-INDEX`](../00-INDEX.md).", ""))
    lines.append(
        f"_Sprint corrente é **{current}**, mas nenhuma lane com frontmatter "
        "foi indexada ainda (Fase 4.A do DOC_REORG popula)._"
    )
    lines.extend(("", *_SPRINT_CURRENT_FOOTER))
    return lines


def _render_open_sections(by_status: dict[str, list[LaneLike]]) -> list[str]:
    """Concatena seções `## Ready/Open/In progress` na ordem editorial, omitindo vazias."""
    out: list[str] = []
    for status in _STATUS_DISPLAY_ORDER:
        bucket = by_status.get(status, [])
        if bucket:
            out.extend(_render_status_section(status, bucket))
    return out


def _render_sprint_body(
    current: str,
    sprint_lanes: list[LaneLike],
    by_status: dict[str, list[LaneLike]],
    header_fn: Callable[[str], list[str]],
) -> list[str]:
    """Renderiza corpo do MD quando há lanes na sprint corrente (status open ou não)."""
    lines = header_fn(f"{_SPRINT_CURRENT_TITLE} — {current}")
    lines.extend(("Volta para [`00-INDEX`](../00-INDEX.md).", ""))
    lines.extend((_summary_line(by_status), ""))
    open_lanes = [lane for bucket in by_status.values() for lane in bucket]
    if open_lanes:
        lines.extend(_render_open_sections(by_status))
    else:
        lines.extend(_render_inspection_listing(sprint_lanes))
    lines.extend(_SPRINT_CURRENT_FOOTER)
    return lines


def render_sprint_current(
    lanes: list[LaneLike],
    available_sprints: set[str],
    header_fn: Callable[[str], list[str]],
) -> list[str]:
    """Monta as linhas do SPRINT_CURRENT.md — entrypoint do renderer."""
    current = _detect_current_sprint(lanes, available_sprints)
    if current is None:
        return _render_no_sprint(header_fn)
    sprint_lanes = _filter_sprint_lanes(lanes, current)
    if not sprint_lanes:
        return _render_no_lanes_in_sprint(header_fn, current)
    by_status = _bucket_lanes_by_status(sprint_lanes)
    return _render_sprint_body(current, sprint_lanes, by_status, header_fn)
