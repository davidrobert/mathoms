"""ADR-343 — snapshot PII-safe + compare de 3 pernas da skill pipeline-review."""

from __future__ import annotations

import copy
import json
from typing import Any

from dev.compare_reviews import build_snapshot, compare_reviews

_CONS_IDS = ["CV1", "CV2", "CV3", "CV6", "CV16", "CV17"]
_RENDER_IDS = ["CV10"]
_DELIVERY_IDS = ["CV9"]
_RUN = {
    "status": "completed",
    "tier_at_run": "premium",
    "total_documents": 40,
    "failed_at_stage": None,
    "minutes": 24.0,
}
_COSTS = [{"cost_usd_cents": 180, "tool_iterations": 1}]
_CALLS = [{"stage": "parecer"}, {"stage": "narrativas"}]
_NR = [{"doc_type": "extratoconta", "n": 2}]
_SENTINEL = object()


def _report_data() -> dict:
    return {
        "patrimonio": {"liquido": 1234567.89, "composicao": {"acoes": 500000.0, "rf": 734567.89}},
        "fluxo_caixa": {"saldo_mensal": 4321.55},
        "ratios": {"poupanca_pct": 22.5},
        "reserva_emergencia": {"meses_alvo": 6},
        "narrativas": {"summaries": {"s1": "texto"}},
        "meta": {"transacoes_total": 100},
        "data_analise": "2026-07-23T10:00:00",
    }


def _cv(ids: list[str] | None = None) -> list[dict]:
    picked = ids if ids is not None else _CONS_IDS + _RENDER_IDS + _DELIVERY_IDS
    return [
        {"check_id": c, "name": "n", "severity": "error", "passed": True, "details": "d"}
        for c in picked
    ]


def _cv_failing(fail: str) -> list[dict]:
    return [
        {"check_id": c, "name": "n", "severity": "error", "passed": c != fail, "details": "d"}
        for c in _CONS_IDS + _RENDER_IDS + _DELIVERY_IDS
    ]


def _meta(run: dict | None, calls: Any) -> dict:
    return {
        "run": run or dict(_RUN),
        "needs_review": _NR,
        "costs": _COSTS,
        "calls": _CALLS if calls is _SENTINEL else calls,
    }


def _snap(
    *,
    report_data: dict | None = None,
    cv_results: list[dict] | None = None,
    run: dict | None = None,
    calls: Any = _SENTINEL,
    parecer: Any = _SENTINEL,
) -> dict:
    return build_snapshot(
        run_id="run-1",
        report_data=report_data or _report_data(),
        cv_results=cv_results if cv_results is not None else _cv(),
        meta=_meta(run, calls),
        parecer={"secoes": list(range(10))} if parecer is _SENTINEL else parecer,
    )


# ─────────────────────────── snapshot PII-safe ───────────────────────────


def test_snapshot_has_no_monetary_literal() -> None:
    blob = json.dumps(_snap(), ensure_ascii=False)
    assert "1234567" not in blob and "4321" not in blob and "734567" not in blob
    assert "500000" not in blob


def test_snapshot_keeps_counts_and_drops_cv_details() -> None:
    snap = _snap()
    assert snap["run_health"]["transacoes_total"] == 100
    assert snap["run_health"]["total_documents"] == 40
    assert all("details" not in c and "name" not in c for c in snap["cross_validation"])
    assert snap["parecer"] == {"status": "ok", "n_secoes": 10, "schema_valid": True}


# ─────────────────────── critério 2: re-run idêntico ───────────────────────


def test_identical_rerun_no_regression() -> None:
    cur_rd = copy.deepcopy(_report_data())
    cur_rd["data_analise"] = "2026-07-24T09:00:00"  # volátil muda; não é regressão
    hard, _soft, _notes = compare_reviews(_snap(), _snap(), _report_data(), cur_rd)
    assert hard == []


# ───────────────── critério 3: skip_llm / tier downgrade suprime ─────────────────


def test_tier_downgrade_suppresses_premium_surfaces() -> None:
    rd_free = copy.deepcopy(_report_data())
    rd_free["narrativas"] = {}  # narrativa esvazia (esperado sem LLM)
    cur = _snap(run={**_RUN, "tier_at_run": "free"}, calls=[], parecer=None, report_data=rd_free)
    hard, _soft, notes = compare_reviews(_snap(), cur, _report_data(), rd_free)
    assert hard == []
    assert "tier_downgrade" in notes


# ─────────── critério 4: regressão injetada → FAIL (e render não falsa-falha) ───────────


def test_zeroed_bucket_is_hard_regression() -> None:
    cur_rd = copy.deepcopy(_report_data())
    cur_rd["patrimonio"]["composicao"]["acoes"] = 0.0  # balde zerado
    hard, _soft, _notes = compare_reviews(_snap(), _snap(), _report_data(), cur_rd)
    assert any("acoes" in h and "zerado" in h for h in hard)


def test_emptied_section_is_hard_regression() -> None:
    rd = copy.deepcopy(_report_data())
    rd["patrimonio"] = {}  # seção determinística esvazia
    hard, _soft, _notes = compare_reviews(_snap(), _snap(report_data=rd), _report_data(), rd)
    assert any("patrimonio" in h and "populated" in h for h in hard)


def test_render_cv_failure_is_soft_not_hard_by_default() -> None:
    cur = _snap(cv_results=_cv_failing("CV10"))  # render CV10 falha → SOFT em default
    hard, soft, _notes = compare_reviews(_snap(), cur, _report_data(), _report_data())
    assert hard == []
    assert any("CV10" in s for s in soft)


def test_strict_promotes_render_cv_to_hard() -> None:
    cur = _snap(cv_results=_cv_failing("CV10"))
    hard, _soft, _notes = compare_reviews(_snap(), cur, _report_data(), _report_data(), strict=True)
    assert any("CV10" in h for h in hard)


def test_delivery_cv9_failure_is_hard_by_default() -> None:
    """ADR-356: CV9 mede ENTREGA de narrativa de seção — parágrafo que sumiu do
    relatório é regressão, não ruído de run incremental. Sai do _RENDER_SOFT."""
    cur = _snap(cv_results=_cv_failing("CV9"))
    hard, soft, _notes = compare_reviews(_snap(), cur, _report_data(), _report_data())
    assert any("CV9" in h for h in hard), hard
    assert not any("CV9" in s for s in soft)


# ─────────────────────────── conservação + volume ───────────────────────────


def test_conservation_cv_pass_to_fail_is_hard() -> None:
    cur = _snap(cv_results=_cv_failing("CV2"))
    hard, _soft, _notes = compare_reviews(_snap(), cur, _report_data(), _report_data())
    assert any("CV2" in h and "falha" in h for h in hard)


def test_tx_drop_is_hard_unless_corpus_shrank() -> None:
    rd_less = copy.deepcopy(_report_data())
    rd_less["meta"]["transacoes_total"] = 60
    hard, _soft, _notes = compare_reviews(
        _snap(), _snap(report_data=rd_less), _report_data(), rd_less
    )
    assert any("transacoes_total" in h for h in hard)

    cur_shrank = _snap(report_data=rd_less, run={**_RUN, "total_documents": 20})
    hard2, _s, _n = compare_reviews(_snap(), cur_shrank, _report_data(), rd_less)
    assert not any("transacoes_total" in h for h in hard2)


def test_value_drift_suppressed_when_corpus_grew() -> None:
    rd_up = copy.deepcopy(_report_data())
    rd_up["patrimonio"]["composicao"]["acoes"] = 800000.0  # +60%
    cur = _snap(run={**_RUN, "total_documents": 55})
    hard, soft, notes = compare_reviews(_snap(), cur, _report_data(), rd_up)
    assert not any("acoes" in h for h in hard)
    assert "corpus_grew" in notes
    assert any("acoes" in s for s in soft)
