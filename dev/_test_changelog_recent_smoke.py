"""Smoke tests do CHANGELOG_RECENT.md — chamados via build_doc_index.py --self-test (F5.C)."""

# Mantido separado para que _test_build_doc_index_smoke.py permaneça <500 linhas
# (guideline CLAUDE.md). Convenção: 1 arquivo de smoke por renderer não-trivial.
# Não é rodado por pytest — snapshot em tests/test_doc_indexes_snapshot.py cobre integração.
#
# A janela ancora na data do entry mais recente (max(date) - 14d), não no relógio:
# o output é função pura das notas, então os asserts não injetam `today`.

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

DOCS = Path(__file__).resolve().parent.parent / "docs"

ChangelogBuildFn = Callable[[list], str]


def _build_entry_raw(
    id_: str, date_: str, summary: str, sprint: str | None, lane: str | None
) -> dict[str, Any]:
    """Monta o dict `raw` (frontmatter), omitindo chaves None."""
    raw: dict[str, Any] = {"id": id_, "type": "changelog-entry", "date": date_, "summary": summary}
    if sprint is not None:
        raw["sprint"] = sprint
    if lane is not None:
        raw["lane"] = lane
    return raw


def _build_entry_note(note_cls: type, raw: dict, sprint: str | None) -> Any:
    """Constrói Note a partir do raw frontmatter (path inferido de sprint+id)."""
    id_ = raw["id"]
    return note_cls(
        path=DOCS / f"sprint/{sprint or 'A11'}/changelog/{id_}.md",
        id=id_,
        type="changelog-entry",
        status="",
        title="",
        sprint=sprint,
        tags=(),
        raw=raw,
    )


def _make_test_changelog_entry(
    note_cls: type,
    *,
    id_: str,
    date_: str,
    summary: str = "",
    sprint: str | None = None,
    lane: str | None = None,
):
    """Helper para construir Note changelog-entry in-memory sem tocar disco."""
    raw = _build_entry_raw(id_, date_, summary, sprint, lane)
    return _build_entry_note(note_cls, raw, sprint)


def _assert_changelog_empty_vault(build_fn: ChangelogBuildFn) -> list[str]:
    """changelog-1: vault sem changelog-entries — stub coerente."""
    out = build_fn([])
    bad: list[str] = []
    if "Nenhuma entrega recente registrada como changelog-entry." not in out:
        bad.append("changelog-1: empty vault — sem stub esperado")
    if "##" in out:
        bad.append("changelog-1: empty vault — não deveria ter seções de dia")
    return bad


def _assert_changelog_today(build_fn: ChangelogBuildFn, note_cls: type) -> list[str]:
    """changelog-2: 1 entry — aparece com título, janela ancorada, summary + lane."""
    entry = _make_test_changelog_entry(
        note_cls,
        id_="CHG-2026-05-07-A10-2",
        date_="2026-05-07",
        summary="Rules-as-code consolidation goals.json",
        sprint="A10",
        lane="[[A10.2]]",
    )
    out = build_fn([entry])
    fragments = (
        "CHANGELOG_RECENT — entregas recentes",
        "Janela de 14 dias a partir da última entrega registrada (2026-05-07).",
        "1 entries entre 2026-05-07 e 2026-05-07.",
        "## 2026-05-07 (1 entries)",
        "- [[CHG-2026-05-07-A10-2]] — Rules-as-code consolidation goals.json (lane [[A10.2]])",
    )
    return [f"changelog-2: fragmento ausente: {f!r}" for f in fragments if f not in out]


def _assert_changelog_old_filtered(build_fn: ChangelogBuildFn, note_cls: type) -> list[str]:
    """changelog-3: entry >14d antes da entrega mais recente é descartada."""
    recent = _make_test_changelog_entry(
        note_cls, id_="CHG-2026-05-07-NEW", date_="2026-05-07", summary="Recente"
    )
    old = _make_test_changelog_entry(
        note_cls, id_="CHG-2026-04-07-OLD", date_="2026-04-07", summary="Velho demais"
    )
    out = build_fn([recent, old])
    bad: list[str] = []
    if "[[CHG-2026-05-07-NEW]]" not in out:
        bad.append("changelog-3: entry âncora (2026-05-07) deveria aparecer")
    if "[[CHG-2026-04-07-OLD]]" in out:
        bad.append("changelog-3: entry 30d antes da âncora não deveria aparecer")
    return bad


def _assert_changelog_single_old_entry_shown(
    build_fn: ChangelogBuildFn, note_cls: type
) -> list[str]:
    """changelog-3b: entry antiga, porém a mais recente da vault, é a âncora e aparece."""
    entry = _make_test_changelog_entry(
        note_cls, id_="CHG-2024-01-15-ONLY", date_="2024-01-15", summary="Única entrega"
    )
    out = build_fn([entry])
    bad: list[str] = []
    if "[[CHG-2024-01-15-ONLY]]" not in out:
        bad.append("changelog-3b: única entry (âncora) deveria aparecer, independente da idade")
    if "Janela de 14 dias a partir da última entrega registrada (2024-01-15)." not in out:
        bad.append("changelog-3b: âncora deveria ser a data da própria entry (2024-01-15)")
    return bad


def _grouping_fixture(note_cls: type) -> list:
    """3 entries em 2 dias — fixture do test changelog-4."""
    return [
        _make_test_changelog_entry(
            note_cls, id_="CHG-2026-05-06-B", date_="2026-05-06", summary="Bee"
        ),
        _make_test_changelog_entry(
            note_cls, id_="CHG-2026-05-07-Z", date_="2026-05-07", summary="Zee"
        ),
        _make_test_changelog_entry(
            note_cls, id_="CHG-2026-05-07-A", date_="2026-05-07", summary="Ay"
        ),
    ]


def _assert_changelog_grouping_and_order(build_fn: ChangelogBuildFn, note_cls: type) -> list[str]:
    """changelog-4: 3 entries em 2 dias — agrupa, dia recente primeiro, id asc no dia."""
    out = build_fn(_grouping_fixture(note_cls))
    bad: list[str] = []
    p_07, p_06 = out.find("## 2026-05-07"), out.find("## 2026-05-06")
    if not (0 < p_07 < p_06):
        bad.append("changelog-4: dia mais recente (2026-05-07) deveria vir antes de 2026-05-06")
    p_a, p_z = out.find("[[CHG-2026-05-07-A]]"), out.find("[[CHG-2026-05-07-Z]]")
    if not (0 < p_a < p_z):
        bad.append("changelog-4: ordem dentro do dia deveria ser id ascendente (A antes de Z)")
    for fragment, msg in (
        ("## 2026-05-07 (2 entries)", "contagem por dia errada para 2026-05-07"),
        ("## 2026-05-06 (1 entries)", "contagem por dia errada para 2026-05-06"),
    ):
        if fragment not in out:
            bad.append(f"changelog-4: {msg}")
    return bad


def _assert_changelog_summary_range(build_fn: ChangelogBuildFn, note_cls: type) -> list[str]:
    """changelog-5: sumário usa min/max das datas filtradas, não intervalo nominal."""
    entries = [
        _make_test_changelog_entry(
            note_cls, id_="CHG-2026-05-01-X", date_="2026-05-01", summary="X"
        ),
        _make_test_changelog_entry(
            note_cls, id_="CHG-2026-05-07-Y", date_="2026-05-07", summary="Y"
        ),
    ]
    out = build_fn(entries)
    if "2 entries entre 2026-05-01 e 2026-05-07." not in out:
        return ["changelog-5: sumário deveria reportar min/max 2026-05-01 e 2026-05-07"]
    return []


def _assert_changelog_no_lane_suffix(build_fn: ChangelogBuildFn, note_cls: type) -> list[str]:
    """changelog-6: entry sem `lane:` — bullet sem sufixo `(lane ...)`."""
    entry = _make_test_changelog_entry(
        note_cls,
        id_="CHG-2026-05-07-NOLANE",
        date_="2026-05-07",
        summary="Sem lane",
    )
    out = build_fn([entry])
    if "[[CHG-2026-05-07-NOLANE]] — Sem lane\n" not in out:
        return [
            "changelog-6: entry sem lane deveria render `- [[id]] — summary`"
            " sem o sufixo `(lane ...)`"
        ]
    return []


def _assert_changelog_generated_relative_links(
    build_fn: ChangelogBuildFn, note_cls: type
) -> list[str]:
    """changelog-7: summary com link relativo é rebaseado para CHANGELOG_RECENT."""
    entry = _make_test_changelog_entry(
        note_cls,
        id_="CHG-2026-05-07-LINK",
        date_="2026-05-07",
        summary="[docs/plan/CENARIOS_ESTRESSE/_README.md](../../../plan/CENARIOS_ESTRESSE/_README.md)",
        sprint="A10",
    )
    out = build_fn([entry])
    if "(../../plan/CENARIOS_ESTRESSE/_README.md)" not in out:
        return ["changelog-7: link relativo deveria ser rebaseado para _generated/"]
    return []


def _assert_changelog_idempotency(build_fn: ChangelogBuildFn, note_cls: type) -> list[str]:
    """changelog-8: build determinístico — 2x mesmo input = mesmo output."""
    entries = [
        _make_test_changelog_entry(
            note_cls, id_="CHG-2026-05-07-IDEMP", date_="2026-05-07", summary="X"
        ),
    ]
    if build_fn(entries) != build_fn(entries):
        return ["changelog-8: build NÃO é idempotente"]
    return []


def run_changelog_smoke_tests(changelog_build_fn: ChangelogBuildFn, note_cls: type) -> list[str]:
    """9 smoke tests do CHANGELOG_RECENT (F5.C). Retorna lista de falhas (vazia = ok)."""
    failures: list[str] = []
    failures.extend(_assert_changelog_empty_vault(changelog_build_fn))
    failures.extend(_assert_changelog_today(changelog_build_fn, note_cls))
    failures.extend(_assert_changelog_old_filtered(changelog_build_fn, note_cls))
    failures.extend(_assert_changelog_single_old_entry_shown(changelog_build_fn, note_cls))
    failures.extend(_assert_changelog_grouping_and_order(changelog_build_fn, note_cls))
    failures.extend(_assert_changelog_summary_range(changelog_build_fn, note_cls))
    failures.extend(_assert_changelog_no_lane_suffix(changelog_build_fn, note_cls))
    failures.extend(_assert_changelog_generated_relative_links(changelog_build_fn, note_cls))
    failures.extend(_assert_changelog_idempotency(changelog_build_fn, note_cls))
    return failures
