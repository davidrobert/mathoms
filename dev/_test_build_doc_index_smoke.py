"""Smoke tests inline para dev/build_doc_index.py (chamados via `--self-test`)."""

# Mantido separado para que build_doc_index.py permaneça <500 linhas (guideline CLAUDE.md).
# NÃO é rodado por pytest — snapshot em tests/test_doc_indexes_snapshot.py cobre integração.
# Estes testes aqui validam comportamento sem precisar de vault populada.

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

DOCS = Path(__file__).resolve().parent.parent / "docs"


def _make_test_note(
    note_cls: type,
    *,
    id_: str,
    status: str = "Decidido",
    title: str = "",
    tags: tuple[str, ...] = (),
    phase: str | None = None,
):
    """Helper para construir Note ADR in-memory sem tocar disco."""
    raw: dict[str, Any] = {"id": id_, "type": "adr", "status": status, "title": title}
    if phase is not None:
        raw["phase"] = phase
    path = DOCS / f"adr/{id_.lower()}.md"
    return note_cls(
        path=path,
        id=id_,
        type="adr",
        status=status,
        title=title,
        tags=tags,
        raw=raw,
    )


def _build_plan_raw(
    id_: str,
    status: str,
    title: str,
    extras: dict[str, Any],
) -> dict[str, Any]:
    """Monta o dict `raw` (frontmatter) para um plan, omitindo chaves None/vazias."""
    raw: dict[str, Any] = {"id": id_, "type": "plan", "status": status, "title": title}
    for key, value in extras.items():
        if value is None or value == ():
            continue
        raw[key] = list(value) if isinstance(value, tuple) else value
    return raw


def _make_test_plan(
    note_cls: type,
    *,
    id_: str,
    status: str = "in_progress",
    title: str = "",
    sprint_atual: str | None = None,
    sprints_envolvidas: tuple[str, ...] = (),
    adrs_canonical: tuple[str, ...] = (),
    paused_at: str | None = None,
    pause_reason: str | None = None,
):
    """Helper para construir Note plan in-memory sem tocar disco."""
    raw = _build_plan_raw(
        id_,
        status,
        title,
        {
            "sprint_atual": sprint_atual,
            "sprints_envolvidas": sprints_envolvidas,
            "adrs_canonical": adrs_canonical,
            "paused_at": paused_at,
            "pause_reason": pause_reason,
        },
    )
    slug = id_.removeprefix("PLAN-").upper()
    return note_cls(
        path=DOCS / f"plan/{slug}/_README.md",
        id=id_,
        type="plan",
        status=status,
        title=title,
        tags=(),
        raw=raw,
    )


def _make_test_lane(
    note_cls: type,
    *,
    id_: str,
    sprint: str,
    status: str = "open",
    plan: str | None = None,
    title: str = "",
    priority: str | None = None,
    branch_slug: str | None = None,
):
    """Helper para construir Note lane in-memory sem tocar disco."""
    raw: dict[str, Any] = {
        "id": id_,
        "type": "lane",
        "status": status,
        "title": title,
        "sprint": sprint,
    }
    if plan is not None:
        raw["plan"] = plan
    if priority is not None:
        raw["priority"] = priority
    if branch_slug is not None:
        raw["branch_slug"] = branch_slug
    return note_cls(
        path=DOCS / f"sprint/{sprint}/lanes/{id_}.md",
        id=id_,
        type="lane",
        status=status,
        title=title,
        sprint=sprint,
        plan=plan,
        tags=(),
        raw=raw,
    )


def _assert_empty_vault(build_fn: Callable[[list], str]) -> list[str]:
    """Test 1: vault vazio (0 ADRs) — output coerente."""
    out = build_fn([])
    bad: list[str] = []
    if "0 ADRs migradas" not in out:
        bad.append("test1: empty vault — sem mensagem de '0 ADRs migradas'")
    if "Sumário por status" in out:
        bad.append("test1: empty vault — não deveria ter sumário")
    return bad


_SINGLE_ADR_FRAGMENTS: tuple[str, ...] = (
    "1 ADR (ADR-090)",
    "## Sumário por status",
    "- **Decidido**: 1",
    "- **Proposto**: 0",
    "- **Roadmap**: 0",
    "## Pipeline DDD/SOLID + Infra+Domínio (Sprint A6)",
    "### Decidido (1)",
    "- [[ADR-090]] — Decimal para valores monetários · phase F5.2",
)


def _assert_single_adr(build_fn: Callable[[list], str], note_cls: type) -> list[str]:
    """Test 2: vault com 1 ADR (estado pós-F1)."""
    note = _make_test_note(
        note_cls,
        id_="ADR-090",
        title="Decimal para valores monetários",
        tags=("type/adr", "area/money", "status/decidido"),
        phase="F5.2",
    )
    out = build_fn([note])
    return [f"test2: fragmento ausente: {f!r}" for f in _SINGLE_ADR_FRAGMENTS if f not in out]


def _assert_load_categories(load_fn: Callable[[], tuple]) -> list[str]:
    """Test 3: _load_adr_categories retorna dicts não-vazios."""
    cats, overrides = load_fn()
    bad: list[str] = []
    if len(cats) < 10:
        bad.append(f"test3: CATEGORIES_LEGACY com {len(cats)} entradas (esperado ≥10)")
    if len(overrides) < 10:
        bad.append(f"test3: OVERRIDES_LEGACY com {len(overrides)} entradas (esperado ≥10)")
    return bad


def _assert_override_wins(category_fn: Callable, note_cls: type) -> list[str]:
    """Test 4: override vence keyword/range (ADR-182 → 'Outras')."""
    note = _make_test_note(
        note_cls,
        id_="ADR-182",
        status="Proposto",
        title="Vault de documentação operacional Obsidian-friendly",
        tags=("type/adr", "area/docs"),
    )
    if category_fn(note) != "Outras":
        return ["test4: ADR-182 deveria cair em 'Outras' via override"]
    return []


def _assert_status_grouping(
    build_fn: Callable[[list], str], note_cls: type
) -> tuple[list[str], list, str]:
    """Test 5: status Proposto/Roadmap aparecem agrupados; retorna notes+out p/ test 6."""
    notes = [
        _make_test_note(note_cls, id_="ADR-001", status="Decidido", title="A"),
        _make_test_note(note_cls, id_="ADR-002", status="Proposto", title="B"),
        _make_test_note(note_cls, id_="ADR-003", status="Roadmap", title="C"),
    ]
    out = build_fn(notes)
    sections = ("### Decidido (1)", "### Proposto (1)", "### Roadmap (1)")
    bad = [f"test5: faltou seção {s!r}" for s in sections if s not in out]
    return bad, notes, out


def _assert_deterministic_order(build_fn: Callable[[list], str], note_cls: type) -> list[str]:
    """Test 7: ordenação determinística por id ascendente mesmo com input embaralhado."""
    shuffled = [
        _make_test_note(note_cls, id_="ADR-003", status="Decidido", title="C"),
        _make_test_note(note_cls, id_="ADR-001", status="Decidido", title="A"),
        _make_test_note(note_cls, id_="ADR-002", status="Decidido", title="B"),
    ]
    out = build_fn(shuffled)
    p1 = out.find("[[ADR-001]]")
    p2 = out.find("[[ADR-002]]")
    p3 = out.find("[[ADR-003]]")
    if not (0 < p1 < p2 < p3):
        return ["test7: ordenação não-determinística por id"]
    return []


_PLAN_RICH_FRAGMENTS: tuple[str, ...] = (
    "2 planos detectados",
    "## Em execução (`in_progress`)",
    "## Pausados (`paused`)",
    "### PLAN-x — Plano X",
    "### PLAN-y — Plano Y",
    "Status: `in_progress`",
    "Status: `paused`",
    "Sprint atual: A11",
    "ADRs canônicas: [[ADR-182]]",
    "Pausado em: 2026-04-15 · Razão: aguarda OKR FY26",
    "_Lanes serão linkadas após Fase 4",
)


def _assert_plan_empty_vault(plan_build_fn: Callable[[list], str]) -> list[str]:
    """Test 8: vault sem plans — output coerente (stub)."""
    out = plan_build_fn([])
    bad: list[str] = []
    if "0 planos em" not in out:
        bad.append("test8: empty vault — sem mensagem '0 planos em'")
    if "## Em execução" in out:
        bad.append("test8: empty vault — não deveria ter seção de status")
    return bad


def _rich_plan_fixture(note_cls: type) -> list:
    """2 plans (in_progress + paused) usados pelo test 9."""
    return [
        _make_test_plan(
            note_cls,
            id_="PLAN-x",
            status="in_progress",
            title="Plano X",
            sprint_atual="A11",
            sprints_envolvidas=("A11",),
            adrs_canonical=("[[ADR-182]]",),
        ),
        _make_test_plan(
            note_cls,
            id_="PLAN-y",
            status="paused",
            title="Plano Y",
            paused_at="2026-04-15",
            pause_reason="aguarda OKR FY26",
        ),
    ]


def _assert_plan_rich(plan_build_fn: Callable[[list], str], note_cls: type) -> list[str]:
    """Test 9: 2 plans em status diferentes + lanes vazias — fragmentos editoriais."""
    out = plan_build_fn(_rich_plan_fixture(note_cls))
    return [f"test9: fragmento ausente: {f!r}" for f in _PLAN_RICH_FRAGMENTS if f not in out]


def _plan_with_lanes_fixture(note_cls: type) -> list:
    """1 plan + 4 lanes (3 ligadas, 1 de outro plano) usados pelo test 10."""
    plan = _make_test_plan(
        note_cls,
        id_="PLAN-z",
        status="in_progress",
        title="Plano Z",
        sprint_atual="A11",
    )
    lanes = [
        _make_test_lane(note_cls, id_="A11.1", sprint="A11", status="shipped", plan="PLAN-z"),
        _make_test_lane(note_cls, id_="A11.2", sprint="A11", status="in_progress", plan="PLAN-z"),
        _make_test_lane(note_cls, id_="A11.3", sprint="A10", status="open", plan="PLAN-z"),
        _make_test_lane(note_cls, id_="A11.4", sprint="A11", status="open", plan="OTHER-PLAN"),
    ]
    return [plan, *lanes]


def _assert_plan_with_lanes(plan_build_fn: Callable[[list], str], note_cls: type) -> list[str]:
    """Test 10: plan + lanes ligadas — contagem por status correta + sprints derivadas."""
    out = plan_build_fn(_plan_with_lanes_fixture(note_cls))
    bad: list[str] = []
    if "1 done · 1 in_progress · 1 open · 0 blocked" not in out:
        bad.append("test10: contagem de lanes errada (esperado 1 done · 1 in_progress · 1 open)")
    if "Sprints envolvidas: A10, A11" not in out:
        bad.append("test10: sprints derivadas das lanes erradas (esperado A10, A11)")
    if "_Lanes serão linkadas após Fase 4" in out:
        bad.append("test10: aviso F4 não deveria aparecer (vault tem lanes)")
    return bad


def _assert_plan_status_order(plan_build_fn: Callable[[list], str], note_cls: type) -> list[str]:
    """Test 11: ordem editorial in_progress > paused > done > cancelled."""
    plans = [
        _make_test_plan(note_cls, id_="PLAN-c", status="cancelled", title="C"),
        _make_test_plan(note_cls, id_="PLAN-d", status="done", title="D"),
        _make_test_plan(note_cls, id_="PLAN-p", status="paused", title="P"),
        _make_test_plan(note_cls, id_="PLAN-i", status="in_progress", title="I"),
    ]
    out = plan_build_fn(plans)
    p_ip = out.find("## Em execução")
    p_paused = out.find("## Pausados")
    p_done = out.find("## Concluídos")
    p_cancelled = out.find("## Cancelados")
    if not (0 < p_ip < p_paused < p_done < p_cancelled):
        return [
            "test11: ordem editorial errada "
            f"(in_progress={p_ip}, paused={p_paused}, done={p_done}, cancelled={p_cancelled})"
        ]
    return []


def _run_adr_smoke_tests(
    build_fn: Callable, load_fn: Callable, category_fn: Callable, note_cls: type
) -> list[str]:
    """7 smoke tests do ADR_INDEX (mantidos do baseline F2.C)."""
    failures: list[str] = []
    failures.extend(_assert_empty_vault(build_fn))
    failures.extend(_assert_single_adr(build_fn, note_cls))
    failures.extend(_assert_load_categories(load_fn))
    failures.extend(_assert_override_wins(category_fn, note_cls))
    bad5, notes, out = _assert_status_grouping(build_fn, note_cls)
    failures.extend(bad5)
    if build_fn(notes) != out:
        failures.append("test6: build_adr_index_md NÃO é idempotente")
    failures.extend(_assert_deterministic_order(build_fn, note_cls))
    return failures


def _assert_plan_idempotency(plan_build_fn: Callable, note_cls: type) -> list[str]:
    """Test 10b: build_plan_progress_md determinístico — 2x mesmo input = mesmo output."""
    sample = [_make_test_plan(note_cls, id_="PLAN-x", status="in_progress", title="X")]
    if plan_build_fn(sample) != plan_build_fn(sample):
        return ["plan-idemp: build_plan_progress_md NÃO é idempotente"]
    return []


def _run_plan_smoke_tests(plan_build_fn: Callable, note_cls: type) -> list[str]:
    """5 smoke tests do PLAN_PROGRESS (F3.C)."""
    failures: list[str] = []
    failures.extend(_assert_plan_empty_vault(plan_build_fn))
    failures.extend(_assert_plan_rich(plan_build_fn, note_cls))
    failures.extend(_assert_plan_idempotency(plan_build_fn, note_cls))
    failures.extend(_assert_plan_with_lanes(plan_build_fn, note_cls))
    failures.extend(_assert_plan_status_order(plan_build_fn, note_cls))
    return failures


def _print_failures(failures: list[str]) -> None:
    """Imprime falhas em stderr (helper de output)."""
    print("✗ smoke tests falharam:", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)


def _print_success(total: int, has_plan: bool, has_sprint: bool) -> None:
    """Imprime mensagem de sucesso com lista de testes rodados."""
    plan_msg = (
        ", plan-empty, plan-rich, plan-idemp, plan-with-lanes, plan-status-order"
        if has_plan
        else ""
    )
    sprint_msg = (
        ", sprint-no-lanes, sprint-ready, sprint-picks-max, "
        "sprint-letter-priority, sprint-wave-agg, sprint-empty-status, sprint-idemp"
        if has_sprint
        else ""
    )
    print(
        f"✓ {total} smoke tests passaram "
        f"(vault vazio, 1 ADR, _load, override, status, idemp, ordem{plan_msg}{sprint_msg})."
    )


def _maybe_run_sprint_tests(sprint_build_fn, note_cls: type) -> tuple[list[str], int]:
    """Importa e roda os 7 smoke tests do SPRINT_CURRENT se o build_fn foi passado."""
    if sprint_build_fn is None:
        return [], 0
    try:
        from _test_sprint_current_smoke import run_sprint_smoke_tests
    except ModuleNotFoundError:  # pragma: no cover
        from dev._test_sprint_current_smoke import run_sprint_smoke_tests
    return run_sprint_smoke_tests(sprint_build_fn, note_cls), 7


def _maybe_run_plan_tests(plan_build_fn, note_cls: type) -> tuple[list[str], int]:
    """Roda os 5 smoke tests do PLAN_PROGRESS se o build_fn foi passado."""
    if plan_build_fn is None:
        return [], 0
    return _run_plan_smoke_tests(plan_build_fn, note_cls), 5


def _collect_all_failures(
    note_cls, build_fn, load_fn, category_fn, plan_build_fn, sprint_build_fn
) -> tuple[list[str], int, int]:
    """Roda os 3 grupos de smoke (ADR + plan + sprint). Retorna (falhas, plan_tests, sprint_tests)."""
    failures = _run_adr_smoke_tests(build_fn, load_fn, category_fn, note_cls)
    plan_failures, plan_tests = _maybe_run_plan_tests(plan_build_fn, note_cls)
    sprint_failures, sprint_tests = _maybe_run_sprint_tests(sprint_build_fn, note_cls)
    failures.extend(plan_failures)
    failures.extend(sprint_failures)
    return failures, plan_tests, sprint_tests


def run_smoke_tests(
    *,
    note_cls: type,
    build_fn,
    load_fn,
    category_fn,
    plan_build_fn=None,
    sprint_build_fn=None,
) -> int:
    """Roda smoke tests; print errors em stderr; return 0 ok / 1 falha."""
    failures, plan_tests, sprint_tests = _collect_all_failures(
        note_cls, build_fn, load_fn, category_fn, plan_build_fn, sprint_build_fn
    )
    if failures:
        _print_failures(failures)
        return 1
    _print_success(
        7 + plan_tests + sprint_tests, plan_build_fn is not None, sprint_build_fn is not None
    )
    return 0
