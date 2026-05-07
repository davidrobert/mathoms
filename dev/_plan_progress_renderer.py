"""Renderer do PLAN_PROGRESS.md — agrega plans + lanes por status (extraído de build_doc_index.py)."""

# Mantém build_doc_index.py <500 linhas (guideline CLAUDE.md). Recebe notas via
# Protocol estrutural (PlanLike/LaneLike) — não importa Note do orquestrador, evita ciclo.
# Spec original: docs/archive/DOC_REORG_PLAN-2026-05-07.md §6.3 (F3.C). Pós-F4, lanes
# já existem em sprint/<X>/lanes/ — output enumera lanes por plano com status.

from __future__ import annotations

from typing import Any, Callable, Protocol

_PLAN_PROGRESS_TITLE = "PLAN_PROGRESS — Status agregado de planos canônicos"
_PLAN_PROGRESS_FOOTER = ("---", "> Regenerar: `python3 dev/build_doc_index.py --inline`")

# Ordem editorial fixa — in_progress primeiro (acionável), cancelled por último (arquivo).
PLAN_STATUS_ORDER: tuple[str, ...] = ("in_progress", "paused", "done", "cancelled", "draft")
PLAN_STATUS_HEADINGS: dict[str, str] = {
    "in_progress": "Em execução (`in_progress`)",
    "paused": "Pausados (`paused`)",
    "done": "Concluídos (`done`)",
    "cancelled": "Cancelados (`cancelled`)",
    "draft": "Rascunhos (`draft`)",
}

# Status de lane que contam como "done" / "open" / "blocked" para a contagem agregada.
# Mantido conservador: planejada (`planned`) cai em "open" porque ainda não foi entregue.
_LANE_STATUS_DONE: frozenset[str] = frozenset({"shipped"})
_LANE_STATUS_IN_PROGRESS: frozenset[str] = frozenset({"in_progress"})
_LANE_STATUS_OPEN: frozenset[str] = frozenset({"open", "planned"})
_LANE_STATUS_BLOCKED: frozenset[str] = frozenset({"blocked"})


class PlanLike(Protocol):
    """Duck-type para Note de plano: campos lidos pelo renderer."""

    id: str
    title: str
    status: str
    raw: dict[str, Any]


class LaneLike(Protocol):
    """Duck-type para Note de lane: campos lidos pelo renderer."""

    id: str
    status: str
    sprint: str | None
    plan: str | None
    raw: dict[str, Any]


def _lanes_for_plan(plan_id: str, lanes: list[LaneLike]) -> list[LaneLike]:
    """Subset de lanes cujo frontmatter `plan:` aponta para o plano dado."""
    return [lane for lane in lanes if lane.plan == plan_id]


def _count_lanes_by_status(plan_lanes: list[LaneLike]) -> dict[str, int]:
    """Bucketiza lanes em done/in_progress/open/blocked/other."""
    counts = {"done": 0, "in_progress": 0, "open": 0, "blocked": 0, "other": 0}
    for lane in plan_lanes:
        if lane.status in _LANE_STATUS_DONE:
            counts["done"] += 1
        elif lane.status in _LANE_STATUS_IN_PROGRESS:
            counts["in_progress"] += 1
        elif lane.status in _LANE_STATUS_OPEN:
            counts["open"] += 1
        elif lane.status in _LANE_STATUS_BLOCKED:
            counts["blocked"] += 1
        else:
            counts["other"] += 1
    return counts


def _format_sprints_envolvidas(plan: PlanLike, plan_lanes: list[LaneLike]) -> str:
    """Lista sprints envolvidas. Prefere derivado das lanes; fallback para declarado."""
    derived = sorted({lane.sprint for lane in plan_lanes if lane.sprint})
    if derived:
        return ", ".join(derived)
    declared = plan.raw.get("sprints_envolvidas")
    if isinstance(declared, list) and declared:
        return ", ".join(str(s) for s in declared)
    return "—"


def _format_adrs_canonical(plan: PlanLike) -> str:
    """Concatena `adrs_canonical` do frontmatter como wikilinks separados por vírgula."""
    raw = plan.raw.get("adrs_canonical")
    if not isinstance(raw, list) or not raw:
        return "—"
    return ", ".join(str(a) for a in raw)


def _format_lanes_line(plan_lanes: list[LaneLike]) -> str:
    """Frase resumo das lanes do plano. '(aguardando F4)' se zero lanes."""
    if not plan_lanes:
        return "_(aguardando F4)_"
    counts = _count_lanes_by_status(plan_lanes)
    parts = [
        f"{counts['done']} done",
        f"{counts['in_progress']} in_progress",
        f"{counts['open']} open",
        f"{counts['blocked']} blocked",
    ]
    if counts["other"]:
        parts.append(f"{counts['other']} outras")
    return " · ".join(parts)


def _format_pause_metadata(plan: PlanLike) -> str | None:
    """Linha extra com `paused_at` + `pause_reason` quando o plano está pausado."""
    if plan.status != "paused":
        return None
    paused_at = plan.raw.get("paused_at") or "?"
    reason = plan.raw.get("pause_reason") or "(razão não declarada)"
    return f"- Pausado em: {paused_at} · Razão: {reason}"


def _render_plan_block(plan: PlanLike, lanes: list[LaneLike]) -> list[str]:
    """Renderiza um bloco markdown para um plano (h3 + bullets de status)."""
    plan_lanes = _lanes_for_plan(plan.id, lanes)
    sprint_atual = plan.raw.get("sprint_atual") or "—"
    out: list[str] = [f"### {plan.id} — {plan.title}", ""]
    out.append(f"- Status: `{plan.status}` · Sprint atual: {sprint_atual}")
    out.append(f"- Sprints envolvidas: {_format_sprints_envolvidas(plan, plan_lanes)}")
    out.append(f"- Lanes: {_format_lanes_line(plan_lanes)}")
    out.append(f"- ADRs canônicas: {_format_adrs_canonical(plan)}")
    pause_line = _format_pause_metadata(plan)
    if pause_line is not None:
        out.append(pause_line)
    out.append("")
    return out


def _ordered_present_statuses(plans: list[PlanLike]) -> list[str]:
    """Status presentes na vault, na ordem editorial canônica + extras alfabéticos."""
    present = {p.status for p in plans if p.status}
    canonical = [s for s in PLAN_STATUS_ORDER if s in present]
    extras = sorted(s for s in present if s not in PLAN_STATUS_ORDER)
    return canonical + extras


def _plan_count_line(plans: list[PlanLike]) -> str:
    """Linha 'N planos detectados em docs/plan/.' (ou singular)."""
    noun = "plano detectado" if len(plans) == 1 else "planos detectados"
    return f"{len(plans)} {noun} em [`docs/plan/`](../../plan/)."


def _f4_pending_note(lanes: list[LaneLike]) -> str | None:
    """Aviso 'lanes serão linkadas após F4' enquanto vault não tem lanes."""
    if any(lane.plan for lane in lanes):
        return None
    return "_Lanes serão linkadas após Fase 4 do DOC_REORG popular `docs/sprint/<X>/lanes/`._"


def _render_status_section(status: str, bucket: list[PlanLike], lanes: list[LaneLike]) -> list[str]:
    """Renderiza um h2 de status + todos os plan blocks ordenados por id."""
    out: list[str] = [f"## {PLAN_STATUS_HEADINGS.get(status, status)}", ""]
    for plan in sorted(bucket, key=lambda p: p.id):
        out.extend(_render_plan_block(plan, lanes))
    return out


def _group_plans_by_status(plans: list[PlanLike]) -> dict[str, list[PlanLike]]:
    """Bucketiza plans por status; status vazio cai em '(sem status)'."""
    by_status: dict[str, list[PlanLike]] = {}
    for plan in plans:
        by_status.setdefault(plan.status or "(sem status)", []).append(plan)
    return by_status


def _render_empty_vault(lines: list[str]) -> list[str]:
    """Output stub quando vault não tem plans."""
    lines.append("_0 planos em `docs/plan/` — Fase 3 do plano DOC_REORG popula 6+ planos._")
    lines.extend(("", *_PLAN_PROGRESS_FOOTER))
    return lines


def render_plan_progress(
    plans: list[PlanLike],
    lanes: list[LaneLike],
    header_fn: Callable[[str], list[str]],
) -> list[str]:
    """Monta as linhas do PLAN_PROGRESS.md. `header_fn(title)` produz cabeçalho de aviso + h1."""
    lines = header_fn(_PLAN_PROGRESS_TITLE)
    lines.extend(("Volta para [`00-INDEX`](../00-INDEX.md).", ""))
    if not plans:
        return _render_empty_vault(lines)
    lines.extend((_plan_count_line(plans), ""))
    pending = _f4_pending_note(lanes)
    if pending is not None:
        lines.extend((pending, ""))
    by_status = _group_plans_by_status(plans)
    for status in _ordered_present_statuses(plans):
        lines.extend(_render_status_section(status, by_status[status], lanes))
    lines.extend(_PLAN_PROGRESS_FOOTER)
    return lines
