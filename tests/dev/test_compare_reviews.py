"""ADR-343 — snapshot PII-safe + compare de 3 pernas da skill pipeline-review."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any

from dev.compare_reviews import build_snapshot, compare_reviews, elapsed_minutes

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
    assert snap["parecer"] == {
        "status": "ok",
        "n_secoes": 10,
        "schema_valid": True,
        "cache_hit": False,
    }


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
    assert any("tier_downgrade" in n for n in notes)


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
    assert any("corpus_grew" in n for n in notes)
    assert any("acoes" in s for s in soft)


# ───── cache hit ≠ downgrade de tier: o falso-verde que zerava o parecer ─────


def _parecer(*, n: int = 10, cache_hit: bool = False) -> dict:
    return {"secoes": list(range(n)), "_meta": {"cache_hit": cache_hit}}


def test_cache_hit_does_not_suppress_parecer_regression() -> None:
    """Parecer do cache tem 0 chamadas LLM mas é íntegro e comparável."""
    # Mutação que mata: reintroduzir `or llm_off` sem a checagem de cache em
    # `_suppressors` ⇒ tier_downgrade liga ⇒ _parecer_regressions devolve [].
    base = _snap(parecer=_parecer(n=10))
    cur = _snap(calls=[], parecer=_parecer(n=4, cache_hit=True))
    hard, _soft, notes = compare_reviews(base, cur, _report_data(), _report_data())
    assert not any("tier_downgrade" in n for n in notes)
    assert any("n_secoes" in h for h in hard)


def test_llm_genuinely_off_still_suppresses() -> None:
    """Guard contra sobre-correção: sem parecer nenhum, a supressão continua."""
    base = _snap(parecer=_parecer())
    cur = _snap(calls=[], parecer=None)
    hard, _soft, notes = compare_reviews(base, cur, _report_data(), _report_data())
    assert any("tier_downgrade" in n for n in notes)
    assert not any("parecer" in h for h in hard)


def test_baseline_sem_cache_hit_degrada_sem_explodir() -> None:
    """Baseline v1 (pré-campo) não quebra e preserva a semântica antiga."""
    base, cur = _snap(parecer=_parecer()), _snap(calls=[], parecer=_parecer())
    for snap in (base, cur):
        del snap["parecer"]["cache_hit"]
    hard, _soft, notes = compare_reviews(base, cur, _report_data(), _report_data())
    assert any("tier_downgrade" in n for n in notes)
    assert hard == []


# ───── duração portável: julianday era SQLite-only (dev) vs Postgres (prod) ─────


def test_elapsed_minutes_aceita_datetime_e_string() -> None:
    """Os dois dialetos têm de produzir o mesmo número."""
    # asyncpg devolve datetime; aiosqlite devolve str. Se divergirem, a duração
    # muda de valor ao trocar de dialeto. Mutação que mata: voltar a duração p/ SQL.
    a, b = datetime(2026, 8, 5, 10, 0), datetime(2026, 8, 5, 10, 24, 30)
    assert elapsed_minutes(a, b) == 24.5
    assert elapsed_minutes(a.isoformat(), b.isoformat()) == 24.5


def test_elapsed_minutes_run_inacabado_e_tz_mista() -> None:
    assert elapsed_minutes("2026-08-05T10:00:00", None) is None
    assert elapsed_minutes(None, None) is None
    assert elapsed_minutes("nao-e-data", "2026-08-05T10:00:00") is None
    mista = elapsed_minutes("2026-08-05T10:00:00+00:00", "2026-08-05T10:30:00")
    assert mista == 30.0


# ───── proveniência: contexto, jamais supressor nem perna de regressão ─────


def _prov(rev: str | None, *, mista: bool = False) -> dict:
    return {"executor_revision": rev, "execucao_mista": mista, "ancestry": "identical"}


def _snap_prov(rev: str | None, *, mista: bool = False, **kw) -> dict:
    snap = _snap(**kw)
    snap["provenance"] = _prov(rev, mista=mista)
    return snap


def test_revisao_divergente_nao_suprime_nenhuma_regressao() -> None:
    """Gate do método: o conjunto de FAIL é BYTE-IDÊNTICO com e sem divergência."""
    # A regressão injetada é de PARECER de propósito: `_parecer_regressions`
    # devolve [] inteiro sob `tier_downgrade`, então é a única classe que expõe
    # proveniência virando supressor. Uma regressão de seção determinística NÃO
    # serve — `tier_downgrade` não a suprime, e o teste passaria mutado.
    base_p = _parecer(n=10)
    cur_p = _parecer(n=3)
    sem, _s1, _n1 = compare_reviews(
        _snap(parecer=base_p), _snap(parecer=cur_p), _report_data(), _report_data()
    )
    assert any("n_secoes" in h for h in sem), "pré-condição: a regressão tem de aparecer"

    b, c = _snap(parecer=base_p), _snap(parecer=cur_p)
    b["provenance"] = _prov("aaaaaaaaaaaa")
    c["provenance"] = _prov("bbbbbbbbbbbb")
    com, _s2, notes = compare_reviews(b, c, _report_data(), _report_data())
    assert com == sem
    assert any("revisão do executor mudou" in n for n in notes)


def test_divergencia_de_revisao_nao_gera_hard() -> None:
    hard, _soft, notes = compare_reviews(
        _snap_prov("aaaaaaaaaaaa"), _snap_prov("bbbbbbbbbbbb"), _report_data(), _report_data()
    )
    assert hard == []
    assert any("dimensão CEGA" in n for n in notes)


def test_execucao_mista_aparece_como_nota() -> None:
    _h, _s, notes = compare_reviews(
        _snap_prov("aaaaaaaaaaaa"),
        _snap_prov("aaaaaaaaaaaa", mista=True),
        _report_data(),
        _report_data(),
    )
    assert any("execução mista" in n for n in notes)


def test_baseline_sem_provenance_degrada_para_nota() -> None:
    """Baseline v1 (pré-F2) não explode; declara que comparou sem proveniência."""
    hard, _soft, notes = compare_reviews(
        _snap(), _snap_prov("aaaaaaaaaaaa"), _report_data(), _report_data()
    )
    assert hard == []
    assert any("desconhecida em um dos runs" in n for n in notes)


def test_snapshot_omite_provenance_quando_nao_ha() -> None:
    assert "provenance" not in _snap()
