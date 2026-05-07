"""Smoke tests do SPRINT_CURRENT.md — chamados via build_doc_index.py --self-test (F4.C)."""

# Mantido separado para que _test_build_doc_index_smoke.py permaneça <500 linhas
# (guideline CLAUDE.md). Convenção: 1 arquivo de smoke por renderer não-trivial.
# Não é rodado por pytest — snapshot em tests/test_doc_indexes_snapshot.py cobre integração.

from __future__ import annotations

from typing import Any, Callable

try:
    from _test_build_doc_index_smoke import _make_test_lane
except (
    ModuleNotFoundError
):  # pragma: no cover — quando importado como dev._test_sprint_current_smoke
    from dev._test_build_doc_index_smoke import _make_test_lane


_SPRINT_READY_FRAGMENTS: tuple[str, ...] = (
    "SPRINT_CURRENT — Lanes da sprint corrente — A11",
    "1 ready · 1 in_progress.",
    "## Ready (1)",
    "- [[A11.W2]] — Apply security findings · priority P0 · branch `a11-w2-security`",
    "## In progress (1)",
    "- [[A11.W4]] — Performance audit · priority P1",
)

_LANE_KW: dict[str, dict[str, Any]] = {
    "A11.W2": {
        "sprint": "A11",
        "status": "ready",
        "title": "Apply security findings",
        "priority": "P0",
        "branch_slug": "a11-w2-security",
    },
    "A11.W4": {
        "sprint": "A11",
        "status": "in_progress",
        "title": "Performance audit",
        "priority": "P1",
    },
    "A11.W1": {"sprint": "A11", "status": "shipped", "title": "Already done"},
}


def _ready_sprint_fixture(note_cls: type) -> list:
    """3 lanes A11 (1 ready P0, 1 in_progress P1, 1 shipped) — fixture do test sprint-2."""
    return [_make_test_lane(note_cls, id_=lane_id, **kw) for lane_id, kw in _LANE_KW.items()]


def _assert_sprint_no_lanes(sprint_build_fn: Callable[[list], str]) -> list[str]:
    """sprint-1: vault sem lanes — stub coerente apontando para Fase 4."""
    out = sprint_build_fn([])
    bad: list[str] = []
    if "Nenhuma lane atomizada ainda" not in out:
        bad.append("sprint-1: empty vault — sem mensagem de stub esperada")
    if "## Ready" in out or "## In progress" in out:
        bad.append("sprint-1: empty vault — não deveria ter seções de status")
    return bad


def _assert_sprint_ready(sprint_build_fn: Callable[[list], str], note_cls: type) -> list[str]:
    """sprint-2: lanes A11 com mix de status — apenas ready/open/in_progress aparecem."""
    out = sprint_build_fn(_ready_sprint_fixture(note_cls))
    bad = [f"sprint-2: fragmento ausente: {f!r}" for f in _SPRINT_READY_FRAGMENTS if f not in out]
    if "Already done" in out:
        bad.append("sprint-2: lane shipped não deveria aparecer (status fora do filtro)")
    return bad


def _assert_sprint_picks_max(sprint_build_fn: Callable[[list], str], note_cls: type) -> list[str]:
    """sprint-3: múltiplas sprints (A10/A11) — escolhe maior (A11)."""
    notes = [
        _make_test_lane(note_cls, id_="A10.1", sprint="A10", status="ready", title="Old"),
        _make_test_lane(note_cls, id_="A11.1", sprint="A11", status="ready", title="New"),
    ]
    out = sprint_build_fn(notes)
    bad: list[str] = []
    if "— A11" not in out:
        bad.append("sprint-3: deveria detectar A11 como sprint corrente (maior número)")
    if "[[A10.1]]" in out:
        bad.append("sprint-3: lane de A10 não deveria aparecer quando A11 é corrente")
    if "[[A11.1]]" not in out:
        bad.append("sprint-3: lane de A11 deveria aparecer")
    return bad


def _assert_sprint_letter_priority(
    sprint_build_fn: Callable[[list], str], note_cls: type
) -> list[str]:
    """sprint-4: A6 ganha de F9 e W6 (peso da letra A>F>W)."""
    notes = [
        _make_test_lane(note_cls, id_="F9.1", sprint="F9", status="ready", title="F-old"),
        _make_test_lane(note_cls, id_="W6.1", sprint="W6", status="ready", title="W-stale"),
        _make_test_lane(note_cls, id_="A6.1", sprint="A6", status="ready", title="A-current"),
    ]
    out = sprint_build_fn(notes)
    if "— A6" not in out:
        return ["sprint-4: A6 deveria ter prioridade sobre F9 e W6 (peso A>F>W)"]
    return []


def _assert_sprint_wave_aggregation(
    sprint_build_fn: Callable[[list], str], note_cls: type
) -> list[str]:
    """sprint-5: lanes em W5/W6 são agregadas a A11 quando A11 é corrente."""
    notes = [
        _make_test_lane(note_cls, id_="A11.1", sprint="A11", status="ready", title="Direct"),
        _make_test_lane(note_cls, id_="A11.W5a", sprint="W5", status="open", title="Wave5"),
        _make_test_lane(note_cls, id_="A11.W6a", sprint="W6", status="in_progress", title="Wave6"),
    ]
    out = sprint_build_fn(notes)
    bad: list[str] = []
    if "— A11" not in out:
        bad.append("sprint-5: A11 deveria ser detectada (max entre A11/W5/W6)")
    for lane_id in ("A11.1", "A11.W5a", "A11.W6a"):
        if f"[[{lane_id}]]" not in out:
            bad.append(f"sprint-5: lane {lane_id} deveria ser agregada a A11")
    return bad


def _assert_sprint_empty_status(
    sprint_build_fn: Callable[[list], str], note_cls: type
) -> list[str]:
    """sprint-6: sprint corrente com lanes mas zero ready/open/in_progress."""
    notes = [
        _make_test_lane(note_cls, id_="A11.1", sprint="A11", status="shipped", title="Done"),
        _make_test_lane(note_cls, id_="A11.2", sprint="A11", status="cancelled", title="Cancel"),
    ]
    out = sprint_build_fn(notes)
    bad: list[str] = []
    if "Nenhuma lane prontidão atual." not in out:
        bad.append("sprint-6: deveria emitir 'Nenhuma lane prontidão atual.'")
    if "## Todas as lanes da sprint" not in out:
        bad.append("sprint-6: deveria listar todas as lanes para inspeção")
    if "[[A11.1]]" not in out or "[[A11.2]]" not in out:
        bad.append("sprint-6: listing de inspeção deveria conter A11.1 e A11.2")
    return bad


def _assert_sprint_idempotency(sprint_build_fn: Callable[[list], str], note_cls: type) -> list[str]:
    """sprint-7: build_sprint_current_md determinístico."""
    sample = _ready_sprint_fixture(note_cls)
    if sprint_build_fn(sample) != sprint_build_fn(sample):
        return ["sprint-7: build_sprint_current_md NÃO é idempotente"]
    return []


def run_sprint_smoke_tests(sprint_build_fn: Callable, note_cls: type) -> list[str]:
    """7 smoke tests do SPRINT_CURRENT (F4.C). Retorna lista de falhas (vazia = ok)."""
    failures: list[str] = []
    failures.extend(_assert_sprint_no_lanes(sprint_build_fn))
    failures.extend(_assert_sprint_ready(sprint_build_fn, note_cls))
    failures.extend(_assert_sprint_picks_max(sprint_build_fn, note_cls))
    failures.extend(_assert_sprint_letter_priority(sprint_build_fn, note_cls))
    failures.extend(_assert_sprint_wave_aggregation(sprint_build_fn, note_cls))
    failures.extend(_assert_sprint_empty_status(sprint_build_fn, note_cls))
    failures.extend(_assert_sprint_idempotency(sprint_build_fn, note_cls))
    return failures
