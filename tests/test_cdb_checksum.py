"""ADR-342 §Emenda 2026-07-23 — apply_cdb_checksum: soma int cents, escopo, escalação."""

from __future__ import annotations

from scripts.e2.validation import apply_cdb_checksum


def _result(posicoes):
    return {"tipo": "cdbresumo", "posicoes": posicoes}


def test_empty_posicoes_escalates() -> None:
    r = _result([])
    apply_cdb_checksum(r, 100.0)
    assert r["requires_llm_fallback"] is True
    assert r["escalation_reason"]["code"] == "extract.empty_result"


def test_sum_matches_total_does_not_escalate() -> None:
    r = _result([{"valor_atual": 100.10}, {"valor_atual": 200.20}, {"valor_atual": 0.70}])
    apply_cdb_checksum(r, 301.00)
    assert not r.get("requires_llm_fallback")


def test_sum_mismatch_escalates_with_dedicated_code() -> None:
    r = _result([{"valor_atual": 100.0}, {"valor_atual": 50.0}])
    apply_cdb_checksum(r, 151.0)
    assert r["requires_llm_fallback"] is True
    assert r["escalation_reason"]["code"] == "extract.investment_sum_mismatch"


def test_total_none_skips_sum_check() -> None:
    r = _result([{"valor_atual": 100.0}])
    apply_cdb_checksum(r, None)
    assert not r.get("requires_llm_fallback")


def test_int_cents_accumulation_no_float_drift() -> None:
    # 0.1 + 0.2 = 0.30000000000000004 em float; int cents fecha exato com 0.30
    r = _result([{"valor_atual": 0.1}, {"valor_atual": 0.2}])
    apply_cdb_checksum(r, 0.30)
    assert not r.get("requires_llm_fallback")


def test_sum_matches_sets_checksum_ok() -> None:
    # A39.l6: pass deixa traço positivo (distingue "passou" de "pulou")
    r = _result([{"valor_atual": 100.0}, {"valor_atual": 50.0}])
    apply_cdb_checksum(r, 150.0)
    assert r.get("checksum_ok") is True
    assert not r.get("requires_llm_fallback")


def test_total_none_sets_skipped_trace() -> None:
    # A39.l6: total agregado ausente → traço skipped (não no-op silencioso), sem escalar
    r = _result([{"valor_atual": 100.0}])
    apply_cdb_checksum(r, None)
    assert r.get("checksum_skipped_no_total") is True
    assert not r.get("checksum_ok")
    assert not r.get("requires_llm_fallback")
