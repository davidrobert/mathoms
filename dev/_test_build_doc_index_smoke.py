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
    """Helper para construir Note in-memory sem tocar disco."""
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


def run_smoke_tests(*, note_cls: type, build_fn, load_fn, category_fn) -> int:
    """Roda os 7 smoke tests; print errors em stderr; return 0 ok / 1 falha."""
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
    if failures:
        print("✗ smoke tests falharam:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("✓ 7 smoke tests passaram (vault vazio, 1 ADR, _load, override, status, idemp, ordem).")
    return 0
