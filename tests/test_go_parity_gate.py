"""Testes do núcleo puro de ``dev/go_parity_gate.py`` (F2 GO_SHELL, [[ADR-150]] §7).

Só a lógica pura (normalização, comparação, verdicts, report). A coleta em DB
(`collect_run_artifacts`) é integração e vive fora deste arquivo.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.go_parity_gate import (  # noqa: E402
    RunComparison,
    _normalize,
    compare_artifact_sets,
    compare_payloads,
    render_report,
    tier1_verdict,
    tier2_verdict,
)

# ─────────────────────────────── normalização ───────────────────────────────


def test_normalize_blanks_identity_and_timestamp_keys():
    payload = {
        "run_id": "abc-123",
        "created_at": "2026-07-08T10:00:00+00:00",
        "finished_at": "2026-07-08T10:05:00+00:00",
        "saldo": 1234.56,
    }
    out = _normalize(payload, ())
    assert out["run_id"] == "<RUN_ID>"
    assert out["created_at"] == "<TS>"
    assert out["finished_at"] == "<TS>"  # sufixo _at
    assert out["saldo"] == 1234.56  # valor de domínio intacto


def test_normalize_replaces_absolute_path_prefix_only():
    payload = {
        "log_path": "/srv/storage/ws42/logs/x.md",
        "arquivo": "itau_extratoconta_BRL_202601_202604-3_reconciled.json",
    }
    out = _normalize(payload, ("/srv/storage/ws42",))
    assert out["log_path"] == "<WS>/logs/x.md"
    assert out["arquivo"].startswith("itau_")  # filename lógico da E3 não é path — intacto


def test_normalize_does_not_sort_lists():
    payload = {"items": [{"id": "b"}, {"id": "a"}]}
    out = _normalize(payload, ())
    assert [it["id"] for it in out["items"]] == ["b", "a"]


# ──────────────────────────────── comparação ────────────────────────────────


def test_compare_payloads_clean_when_only_identity_differs():
    old = {"run_id": "r1", "generated_at": "2026-07-08T00:00:00", "total": 100.0}
    new = {"run_id": "r2", "generated_at": "2026-07-08T09:99:99", "total": 100.0}
    assert compare_payloads(old, new) == []


def test_compare_payloads_flags_monetary_delta_in_cents():
    diffs = compare_payloads({"total": 100.00}, {"total": 100.50})
    assert len(diffs) == 1
    assert diffs[0].kind == "value_delta"
    assert diffs[0].delta_cents == 50


def test_compare_artifact_sets_pairs_and_flags_missing_extra():
    old = {("E3", "itau"): {"total": 10.0}, ("E4", "despesas"): {"total": 5.0}}
    new = {("E3", "itau"): {"total": 10.0}, ("E5", "analise"): {"score": 1}}
    cmp = compare_artifact_sets(old, new)
    assert cmp.only_in_old == [("E4", "despesas")]
    assert cmp.only_in_new == [("E5", "analise")]
    assert cmp.is_clean is False


def test_compare_artifact_sets_clean_when_identical():
    a = {("E3", "itau"): {"total": 10.0, "run_id": "x"}}
    b = {("E3", "itau"): {"total": 10.0, "run_id": "y"}}
    assert compare_artifact_sets(a, b).is_clean is True


# ───────────────────────────────── verdicts ─────────────────────────────────


def _clean() -> RunComparison:
    return RunComparison()


def _dirty() -> RunComparison:
    return RunComparison(only_in_new=[("E5", "analise")])


def test_tier1_pass_requires_clean_main_and_clean_control():
    ok, _ = tier1_verdict(_clean(), _clean())
    assert ok is True


def test_tier1_fails_on_dirty_main():
    ok, reason = tier1_verdict(_dirty(), _clean())
    assert ok is False and "value-exact" in reason


def test_tier1_fails_when_control_not_zero():
    """Guarda anti-mascaramento: controle Py↔Py não-zero = gate não está pronto."""
    ok, reason = tier1_verdict(_clean(), _dirty())
    assert ok is False and "controle" in reason


def test_tier2_pass_when_go_divergence_subset_of_control():
    from dev.go_parity_gate import FieldDiff  # noqa: E402

    shared = {("E5", "analise"): [FieldDiff("prosa", "value_delta", "a", "b")]}
    main = RunComparison(diffs_by_artifact=shared)
    control = RunComparison(diffs_by_artifact=shared)
    ok, _ = tier2_verdict(main, control)
    assert ok is True


def test_tier2_fails_on_leaked_path_outside_control():
    from dev.go_parity_gate import FieldDiff  # noqa: E402

    main = RunComparison(
        diffs_by_artifact={("E3", "itau"): [FieldDiff("total", "value_delta", 1, 2)]}
    )
    ok, reason = tier2_verdict(main, _clean())
    assert ok is False and "fora do piso" in reason


def test_tier2_requires_control_run():
    ok, reason = tier2_verdict(_clean(), None)
    assert ok is False and "control-run" in reason


# ─────────────────────────────────── report ─────────────────────────────────


def test_render_report_clean_and_dirty():
    assert "0 divergências" in render_report(_clean(), label="x")
    assert "só no lado B" in render_report(_dirty(), label="x")


# ─────────────────────────── eventos WS (Tier-2) ────────────────────────────


def _ws_set(events):
    from dev.go_parity_gate import WS_ARTIFACT  # noqa: E402

    return {WS_ARTIFACT: {"events": events}}


def test_ws_events_sequence_divergence_detected():
    py = _ws_set(
        [{"event": "stage_started", "stage": "E3"}, {"event": "stage_completed", "stage": "E3"}]
    )
    go = _ws_set(
        [{"event": "stage_completed", "stage": "E3"}, {"event": "stage_started", "stage": "E3"}]
    )
    cmp = compare_artifact_sets(py, go)
    assert cmp.is_clean is False


def test_ws_events_identity_only_is_clean():
    py = _ws_set([{"event": "run_started", "run_id": "a", "timestamp": "2026-07-08T00:00:00"}])
    go = _ws_set([{"event": "run_started", "run_id": "b", "timestamp": "2026-07-08T09:59:59"}])
    assert compare_artifact_sets(py, go).is_clean is True


def test_ws_events_missing_event_detected():
    py = _ws_set([{"event": "stage_started"}, {"event": "stage_completed"}])
    go = _ws_set([{"event": "stage_started"}])
    assert compare_artifact_sets(py, go).is_clean is False


def test_with_ws_injects_and_none_is_noop():
    from dev.go_parity_gate import WS_ARTIFACT, _with_ws  # noqa: E402

    base = {("E3", "itau"): {"total": 1.0}}
    injected = _with_ws(base, [{"event": "run_started"}])
    assert injected[WS_ARTIFACT] == {"events": [{"event": "run_started"}]}
    assert _with_ws(base, None) == base
