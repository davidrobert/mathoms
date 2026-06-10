"""Testes do núcleo puro de ``dev/golden_diff.py`` (A23.l2)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.golden_diff import (  # noqa: E402
    FieldDiff,
    ManifestEntry,
    check_manifest,
    diff_golden,
    is_monetary,
    to_cents,
)


def _kinds(diffs: list[FieldDiff]) -> dict[str, str]:
    return {d.path: d.kind for d in diffs}


def test_to_cents_via_decimal_no_float_drift():
    assert to_cents(1234.56) == 123456
    assert to_cents("0.575") == 58  # ROUND_HALF_UP, sem erro de float
    assert to_cents(0) == 0
    assert to_cents(500_000.0) == 50_000_000


def test_to_cents_rejects_non_numeric():
    with pytest.raises(ValueError):
        to_cents("abc")


def test_is_monetary_default_and_non_monetary_allowlist():
    assert is_monetary("patrimonio.bruto")
    assert is_monetary("patrimonio.composicao[Caixa].valor")
    assert is_monetary("goals.if_meta")
    assert is_monetary("score.valor")  # valor é monetário-por-default (manifesto justifica)
    assert not is_monetary("ratios.taxa_endividamento_pct")
    assert not is_monetary("score.max")
    assert not is_monetary("if_kpis.idade_david")
    assert not is_monetary("if.ano_if")
    assert not is_monetary("reserva.cobertura_meses")
    assert not is_monetary("rentabilidade.retorno_real_anual_pct")
    assert not is_monetary("_report_lineage.source_document_count")
    assert not is_monetary("e3.transacoes_total")


def test_unchanged_is_classified():
    a = {"patrimonio": {"bruto": 100.0, "liquido": 100.0}}
    diffs = diff_golden(a, dict(a))
    assert all(d.kind == "unchanged" for d in diffs)


def test_value_delta_monetary_emits_cents():
    old = {"patrimonio": {"liquido": 400_000.0}}
    new = {"patrimonio": {"liquido": 399_500.0}}
    diffs = [d for d in diff_golden(old, new) if d.kind == "value_delta"]
    assert len(diffs) == 1
    assert diffs[0].path == "patrimonio.liquido"
    assert diffs[0].delta_cents == -50_000
    assert diffs[0].is_monetary_value_delta()


def test_value_delta_non_monetary_has_no_cents():
    old = {"ratios": {"taxa_endividamento_pct": 10.0}}
    new = {"ratios": {"taxa_endividamento_pct": 12.0}}
    [d] = [d for d in diff_golden(old, new) if d.kind == "value_delta"]
    assert d.delta_cents is None
    assert not d.is_monetary_value_delta()


def test_new_and_removed_keys():
    old = {"a": {"x": 1.0}}
    new = {"a": {"y": 2.0}}
    kinds = _kinds(diff_golden(old, new))
    assert kinds["a.x"] == "removed"
    assert kinds["a.y"] == "new"


def test_array_paired_by_natural_key_reorder_is_unchanged():
    old = {"composicao": [{"categoria": "A", "valor": 10.0}, {"categoria": "B", "valor": 20.0}]}
    new = {"composicao": [{"categoria": "B", "valor": 20.0}, {"categoria": "A", "valor": 10.0}]}
    diffs = diff_golden(old, new)
    assert all(d.kind == "unchanged" for d in diffs), _kinds(diffs)


def test_array_natural_key_detects_value_delta_in_item():
    old = {"composicao": [{"categoria": "A", "valor": 10.0}]}
    new = {"composicao": [{"categoria": "A", "valor": 11.0}]}
    [d] = [d for d in diff_golden(old, new) if d.kind == "value_delta"]
    assert d.path == "composicao[A].valor"
    assert d.delta_cents == 100


def test_moved_pairs_same_leaf_same_nonzero_value():
    old = {"bloco_a": {"saldo": 1500.0}, "bloco_b": {}}
    new = {"bloco_a": {}, "bloco_b": {"saldo": 1500.0}}
    diffs = diff_golden(old, new)
    moved = [d for d in diffs if d.kind == "moved"]
    assert len(moved) == 1
    assert moved[0].path == "bloco_b.saldo"


def test_zero_value_does_not_trigger_false_moved():
    old = {"a": {"saldo": 0.0}, "b": {}}
    new = {"a": {}, "b": {"saldo": 0.0}}
    diffs = diff_golden(old, new)
    assert not [d for d in diffs if d.kind == "moved"]


def test_changed_and_relocated_value_does_not_become_moved():
    old = {"a": {"saldo": 1500.0}, "b": {}}
    new = {"a": {}, "b": {"saldo": 1600.0}}
    kinds = _kinds(diff_golden(old, new))
    assert "moved" not in kinds.values()
    assert kinds["a.saldo"] == "removed"
    assert kinds["b.saldo"] == "new"


def _entry(old_cents: int, new_cents: int) -> ManifestEntry:
    return ManifestEntry(
        "g1",
        "patrimonio.liquido",
        old_cents,
        new_cents,
        "ADR-271",
        "dedup cross-year colapsa conta conjunta",
        "pipeline/domain/services/e5_serialization.py:312",
    )


def test_check_manifest_covered_vs_uncovered():
    old = {"patrimonio": {"liquido": 400_000.0}}
    new = {"patrimonio": {"liquido": 399_500.0}}
    diffs = diff_golden(old, new)
    entry = _entry(40_000_000, 39_950_000)

    uncovered, orphans = check_manifest(diffs, [entry], "g1")
    assert not uncovered and not orphans

    uncovered, orphans = check_manifest(diffs, [], "g1")
    assert len(uncovered) == 1 and not orphans


def test_check_manifest_orphan_entry_fails():
    old = {"patrimonio": {"liquido": 400_000.0}}
    diffs = diff_golden(old, dict(old))  # sem mudança
    entry = _entry(40_000_000, 39_950_000)
    uncovered, orphans = check_manifest(diffs, [entry], "g1")
    assert not uncovered and len(orphans) == 1


def test_check_manifest_wrong_cents_does_not_cover():
    old = {"patrimonio": {"liquido": 400_000.0}}
    new = {"patrimonio": {"liquido": 399_500.0}}
    diffs = diff_golden(old, new)
    entry = _entry(40_000_000, 39_999_999)  # cents errado
    uncovered, orphans = check_manifest(diffs, [entry], "g1")
    assert len(uncovered) == 1 and len(orphans) == 1


def test_diff_is_deterministic_sorted():
    old = {"z": 1.0, "a": 2.0, "m": {"k": 3.0}}
    new = {"z": 1.5, "a": 2.5, "m": {"k": 3.5}}
    paths = [d.path for d in diff_golden(old, new)]
    assert paths == sorted(paths)


# ──────────────────── F2-DB6: justificativa obrigatória ────────────────────


def _write_manifest(tmp_path, entries) -> Path:
    import yaml

    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump(entries), encoding="utf-8")
    return p


_FULL_ENTRY = {
    "golden": "g1",
    "path": "patrimonio.liquido",
    "old_cents": 40_000_000,
    "new_cents": 39_950_000,
    "adr": "ADR-271",
    "rationale": "dedup cross-year colapsa conta conjunta",
    "ref": "pipeline/domain/services/e5_serialization.py:312",
}


def test_load_manifest_accepts_full_entry(tmp_path):
    from dev.golden_diff import load_manifest

    entries = load_manifest(_write_manifest(tmp_path, [_FULL_ENTRY]))
    assert entries[0].adr == "ADR-271"
    assert entries[0].ref.endswith(":312")


@pytest.mark.parametrize("missing", ["adr", "rationale", "ref"])
def test_load_manifest_rejects_missing_justification(tmp_path, missing):
    from dev.golden_diff import load_manifest

    entry = {k: v for k, v in _FULL_ENTRY.items() if k != missing}
    with pytest.raises(ValueError, match=missing):
        load_manifest(_write_manifest(tmp_path, [entry]))


@pytest.mark.parametrize(
    ("field", "bad", "expect"),
    [
        ("adr", "271", "adr deve casar"),
        ("ref", "e5_serialization.py", "file:line"),
        ("rationale", "   ", "rationale"),
    ],
)
def test_load_manifest_rejects_bad_shape(tmp_path, field, bad, expect):
    from dev.golden_diff import load_manifest

    entry = {**_FULL_ENTRY, field: bad}
    with pytest.raises(ValueError, match=expect):
        load_manifest(_write_manifest(tmp_path, [entry]))
