"""Renderer do SPRINT_CURRENT.md — lanes da sprint corrente filtradas por status (F4.C)."""

# Mantém build_doc_index.py <500 linhas (guideline CLAUDE.md). Recebe notas via
# Protocol estrutural (LaneLike) — não importa Note do orquestrador, evita ciclo.
# Spec: docs/plan/DOC_REORG/_README.md §6.4 (Fase 4, item C).
#
# Detecção de sprint corrente — duas vias:
# 1. Declarativa (preferida): `sprint_status: current` no frontmatter do MOC
#    `docs/sprint/<X>/_README.md`. Resolve casos onde sprints encavalam
#    (ex.: A11 ainda tem lanes open e A12 já começou — heurística "max número"
#    erra; declaração editorial vence). Validador em build_doc_index.py
#    garante exatamente 1 sprint com `current` quando há ≥1 MOC com `sprint_status`.
# 2. Fallback heurístico: prioridade por letra (A > F > W), maior número.
#    Sprints "A" são oficiais; "F" são fases legadas; "W" são ondas dentro
#    de uma sprint "A". Quando A11 é corrente, lanes com sprint W5/W6 são
#    agregadas (waves pertencem a A11).

from __future__ import annotations

import re
from typing import Any, Callable, Protocol

_SPRINT_CURRENT_TITLE = "SPRINT_CURRENT — Lanes da sprint corrente"
_SPRINT_CURRENT_FOOTER = (
    "---",
    "> Regenerar: `python3 dev/build_doc_index.py --inline`",
    ">",
    "> **Este arquivo não vê ocupação.** Ele deriva do frontmatter, que ninguém",
    "> escreve no pickup: sessão que abriu worktree e ainda não commitou é",
    "> invisível aqui, em `git for-each-ref` e em `gh pr list`. Antes de pegar",
    "> qualquer lane abaixo, rode `python3 dev/lane_pickup.py <id>`.",
)

# Status de lane que contam como "prontos para pickup" / "em execução".
# `consumed` é status de TRACK (não lane) e nunca aparece aqui.
LANE_STATUS_OPEN: frozenset[str] = frozenset({"ready", "open", "in_progress"})
_STATUS_DISPLAY_ORDER: tuple[str, ...] = ("ready", "open", "in_progress")
_STATUS_HEADINGS: dict[str, str] = {
    "ready": "Ready",
    "open": "Open",
    "in_progress": "In progress",
}

# `blocked` ganha seção própria: enquanto ele só sumia daqui, lane P0 ficava
# invisível exatamente quando a dependência shippava e ela virava pegável
# (medido 2× na A40 — _README §Delta 2026-08-06 e §Delta 2026-08-07). O gate
# `dev/check_lane_status_predicate.py` mata o caso derivável; esta seção cobre
# o resto, mostrando o bloqueador em vez de esconder a lane.
_LANE_STATUS_BLOCKED = "blocked"
_TERMINAL_STATUS: frozenset[str] = frozenset({"shipped", "cancelled"})

# `[[Alvo]]`, `[[Alvo|apelido]]`, `[[Alvo#anchor]]` — captura só o alvo.
_WIKILINK_TARGET_RE = re.compile(r"^\[\[([^\]|#]+)")

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


def _detect_current_sprint(
    lanes: list[LaneLike],
    available_sprints: set[str],
    sprint_statuses: dict[str, str] | None = None,
) -> str | None:
    """Sprint corrente: declaração `sprint_status: current` no MOC vence heurística max."""
    declared = _declared_current(sprint_statuses or {})
    if declared is not None:
        return declared
    candidates = available_sprints or {lane.sprint for lane in lanes if lane.sprint}
    if not candidates:
        return None
    return max(_eligible_sprints(candidates), key=_sprint_priority_key)


def _declared_current(sprint_statuses: dict[str, str]) -> str | None:
    """Sprint cujo MOC declara `sprint_status: current`. None se nenhuma declara."""
    current = [sprint for sprint, status in sprint_statuses.items() if status == "current"]
    if not current:
        return None
    return current[0]


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


def _blocked_lanes(lanes: list[LaneLike]) -> list[LaneLike]:
    """Lanes `blocked` da sprint — listadas para não sumirem ao ficarem pegáveis."""
    return [lane for lane in lanes if lane.status == _LANE_STATUS_BLOCKED]


# Sem contagem: o valor é função da vault INTEIRA, então dois PRs disjuntos colidem na
# mesma linha — e quando ambos incrementam, o merge fica limpo e MENTE (lost update).
# A lista de status logo abaixo carrega a mesma informação, uma linha por lane, e o merge
# de linha do git resolve os casos disjuntos sozinho (A40.l59 §fila de merge, 2026-08-24).
def _summary_line(by_status: dict[str, list[LaneLike]], blocked: int = 0) -> str:
    """Frase 'ready · in_progress · open · blocked' — status presentes, sem contagem."""
    parts = [status for status in _STATUS_DISPLAY_ORDER if by_status.get(status)]
    if blocked:
        parts.append("blocked")
    if not parts:
        return "Nenhuma lane prontidão atual."
    return " · ".join(parts) + "."


def _dependency_ids(lane: LaneLike) -> list[str]:
    """Alvos de `depends_on`, sem os colchetes do wikilink."""
    out: list[str] = []
    for raw in lane.raw.get("depends_on") or []:
        match = _WIKILINK_TARGET_RE.match(str(raw))
        if match:
            out.append(match.group(1).strip())
    return out


def _areas(lane: LaneLike) -> list[str]:
    """Tags `area/<x>` viram rótulo — evita abrir a lane só para saber o stack."""
    prefix = "area/"
    return [tag[len(prefix) :] for tag in lane.raw.get("tags") or [] if str(tag).startswith(prefix)]


def _pending_dependencies(lane: LaneLike, status_by_id: dict[str, str]) -> list[str]:
    """Deps conhecidas que ainda não são terminais, formatadas com o status."""
    pending: list[str] = []
    for dep_id in _dependency_ids(lane):
        status = status_by_id.get(dep_id)
        if status is not None and status not in _TERMINAL_STATUS:
            pending.append(f"{dep_id} ({status})")
    return pending


def _dependency_note(lane: LaneLike, status_by_id: dict[str, str]) -> list[str]:
    """Nota de dependência: só aparece quando há dep pendente."""
    pending = _pending_dependencies(lane, status_by_id)
    if not pending:
        return []
    if lane.raw.get("partial_delivery") is True:
        return [f"⚠️ entrega parcial — dep pendente: {', '.join(pending)}"]
    return [f"⛔ dep pendente: {', '.join(pending)}"]


def _lane_extras(lane: LaneLike, status_by_id: dict[str, str]) -> list[str]:
    """Campos que decidem pickup — a pergunta se responde aqui, não no arquivo."""
    extras: list[str] = []
    priority = lane.raw.get("priority")
    if priority not in (None, ""):
        extras.append(f"priority {priority}")
    areas = _areas(lane)
    if areas:
        extras.append(f"área {'/'.join(areas)}")
    extras.extend(_dependency_note(lane, status_by_id))
    branch_slug = lane.raw.get("branch_slug")
    if branch_slug not in (None, ""):
        extras.append(f"branch `{branch_slug}`")
    return extras


def _format_lane_line(lane: LaneLike, status_by_id: dict[str, str] | None = None) -> str:
    """Linha por lane: wikilink + título + o que decide pickup."""
    extras = _lane_extras(lane, status_by_id or {})
    suffix = f" · {' · '.join(extras)}" if extras else ""
    title = lane.title or lane.id
    return f"- [[{lane.id}]] — {title}{suffix}"


def _lane_sort_key(lane: LaneLike) -> str:
    """Ordena lanes por id ascendente (estável dentro do bucket de status)."""
    return lane.id


def _render_status_section(
    status: str, bucket: list[LaneLike], status_by_id: dict[str, str]
) -> list[str]:
    """Renderiza um h2 de status + bullets de lanes ordenadas por id."""
    heading = _STATUS_HEADINGS.get(status, status)
    out: list[str] = [f"## {heading}", ""]
    for lane in sorted(bucket, key=_lane_sort_key):
        out.append(_format_lane_line(lane, status_by_id))
    out.append("")
    return out


def _render_blocked_section(bucket: list[LaneLike], status_by_id: dict[str, str]) -> list[str]:
    """Lanes `blocked` com o bloqueador à vista — esconder a lane esconde o destravamento."""
    out: list[str] = [
        "## Blocked",
        "",
        "_Não pegáveis. Listadas porque `blocked` que fica stale some daqui "
        "justamente quando a dependência ship e a lane vira pegável._",
        "",
    ]
    for lane in sorted(bucket, key=_lane_sort_key):
        out.append(_format_lane_line(lane, status_by_id))
    out.append("")
    return out


def _render_inspection_listing(
    sprint_lanes: list[LaneLike], status_by_id: dict[str, str]
) -> list[str]:
    """Quando ready/open/in_progress está vazio: lista todas as lanes para inspeção."""
    out: list[str] = ["## Todas as lanes da sprint (para inspeção)", ""]
    by_status: dict[str, list[LaneLike]] = {}
    for lane in sprint_lanes:
        by_status.setdefault(lane.status or "(sem status)", []).append(lane)
    for status in sorted(by_status):
        out.extend(_render_inspection_bucket(status, by_status[status], status_by_id))
    return out


def _render_inspection_bucket(
    status: str, bucket: list[LaneLike], status_by_id: dict[str, str]
) -> list[str]:
    """Um h3 de status dentro da listagem de inspeção."""
    out: list[str] = [f"### {status}", ""]
    for lane in sorted(bucket, key=_lane_sort_key):
        out.append(_format_lane_line(lane, status_by_id))
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


def _render_open_sections(
    by_status: dict[str, list[LaneLike]], status_by_id: dict[str, str]
) -> list[str]:
    """Concatena seções `## Ready/Open/In progress` na ordem editorial, omitindo vazias."""
    out: list[str] = []
    for status in _STATUS_DISPLAY_ORDER:
        bucket = by_status.get(status, [])
        if bucket:
            out.extend(_render_status_section(status, bucket, status_by_id))
    return out


def _render_sprint_body(
    current: str,
    sprint_lanes: list[LaneLike],
    by_status: dict[str, list[LaneLike]],
    header_fn: Callable[[str], list[str]],
    status_by_id: dict[str, str],
) -> list[str]:
    """Renderiza corpo do MD quando há lanes na sprint corrente (status open ou não)."""
    blocked = _blocked_lanes(sprint_lanes)
    lines = header_fn(f"{_SPRINT_CURRENT_TITLE} — {current}")
    lines.extend(("Volta para [`00-INDEX`](../00-INDEX.md).", ""))
    lines.extend((_summary_line(by_status, len(blocked)), ""))
    lines.extend(_render_lane_listing(sprint_lanes, by_status, status_by_id))
    if blocked:
        lines.extend(_render_blocked_section(blocked, status_by_id))
    lines.extend(_SPRINT_CURRENT_FOOTER)
    return lines


def _render_lane_listing(
    sprint_lanes: list[LaneLike],
    by_status: dict[str, list[LaneLike]],
    status_by_id: dict[str, str],
) -> list[str]:
    """Seções por status quando há lane pegável; listagem de inspeção quando não há."""
    open_lanes = [lane for bucket in by_status.values() for lane in bucket]
    if open_lanes:
        return _render_open_sections(by_status, status_by_id)
    return _render_inspection_listing(sprint_lanes, status_by_id)


def _status_by_id(lanes: list[LaneLike]) -> dict[str, str]:
    """Status de TODA lane do vault — a dep de uma lane da sprint pode viver em outra."""
    return {lane.id: lane.status for lane in lanes if lane.id}


def render_sprint_current(
    lanes: list[LaneLike],
    available_sprints: set[str],
    header_fn: Callable[[str], list[str]],
    sprint_statuses: dict[str, str] | None = None,
) -> list[str]:
    """Monta as linhas do SPRINT_CURRENT.md — entrypoint do renderer."""
    current = _detect_current_sprint(lanes, available_sprints, sprint_statuses)
    if current is None:
        return _render_no_sprint(header_fn)
    sprint_lanes = _filter_sprint_lanes(lanes, current)
    if not sprint_lanes:
        return _render_no_lanes_in_sprint(header_fn, current)
    by_status = _bucket_lanes_by_status(sprint_lanes)
    return _render_sprint_body(current, sprint_lanes, by_status, header_fn, _status_by_id(lanes))
