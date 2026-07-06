"""A22.l4 — sinais de drift do parecer (janela (prompt_version, model_name))."""

from __future__ import annotations

from collections import namedtuple

import pytest

from backend.app.services import parecer_drift_monitor as mon

_Row = namedtuple(
    "_Row",
    [
        "prompt_version",
        "model_name",
        "confidence",
        "needs_review",
        "tokens",
        "cost_usd",
        "duration_ms",
    ],
)


def _rows(
    version: str, model: str, n: int, *, conf=0.9, review=False, tokens=1000, cost=0.05, dur=30_000
):
    return [_Row(version, model, conf, review, tokens, cost, dur) for _ in range(n)]


def _signals_for(monkeypatch, rows):
    monkeypatch.setattr(mon, "_fetch_recent_rows", lambda db, ws: rows)
    return mon.compute_parecer_drift_signals(db=None, workspace_id="ws1")


def _by_name(signals):
    return {s.signal: s for s in signals}


def test_sem_geracao_retorna_vazio(monkeypatch):
    assert _signals_for(monkeypatch, []) == []


def test_janela_pequena_vira_insufficient_data(monkeypatch):
    signals = _signals_for(monkeypatch, _rows("2.0.0", "m1", 3) + _rows("1.0.0", "m1", 10))
    sample = _by_name(signals)["window_sample"]
    assert sample.verdict == "insufficient_data"
    assert sample.n_current == 3 and sample.n_baseline == 10


def test_baseline_ruidoso_e_pulado_para_versao_anterior_com_n_minimo(monkeypatch):
    rows = _rows("3.0.0", "m1", 10) + _rows("2.0.0", "m1", 2) + _rows("1.0.0", "m1", 10, conf=0.5)
    conf = _by_name(_signals_for(monkeypatch, rows))["confidence_delta"]
    assert conf.baseline == pytest.approx(0.5)


def test_needs_review_salto_grande_warn_e_ruido_ok(monkeypatch):
    base = _rows("1.0.0", "m1", 10, review=False)
    salto = _rows("2.0.0", "m1", 10, review=True)
    assert (
        _by_name(_signals_for(monkeypatch, salto + base))["needs_review_rate_delta"].verdict
        == "warn"
    )

    ruido = _rows("2.0.0", "m1", 9, review=False) + _rows("2.0.0", "m1", 1, review=True)
    assert (
        _by_name(_signals_for(monkeypatch, ruido + base))["needs_review_rate_delta"].verdict == "ok"
    )


def test_tokens_acima_de_30pct_warn(monkeypatch):
    rows = _rows("2.0.0", "m1", 10, tokens=2000) + _rows("1.0.0", "m1", 10, tokens=1000)
    by = _by_name(_signals_for(monkeypatch, rows))
    assert by["tokens_mean_delta"].verdict == "warn"
    assert by["cost_mean_delta"].verdict == "ok"


def test_duration_p95_estourada_warn(monkeypatch):
    rows = _rows("2.0.0", "m1", 10, dur=243_000) + _rows("1.0.0", "m1", 10, dur=60_000)
    assert _by_name(_signals_for(monkeypatch, rows))["duration_p95_delta"].verdict == "warn"


def test_model_swap_na_mesma_versao_warn_imediato(monkeypatch):
    rows = _rows("2.0.0", "m2", 1) + _rows("2.0.0", "m1", 10) + _rows("1.0.0", "m1", 10)
    swap = _by_name(_signals_for(monkeypatch, rows))["model_swap_within_version"]
    assert swap.verdict == "warn" and swap.value == 2.0


def test_todo_sinal_declara_baseline_kind_e_sem_conteudo(monkeypatch):
    rows = _rows("2.0.0", "m1", 10) + _rows("1.0.0", "m1", 10)
    for s in _signals_for(monkeypatch, rows):
        assert s.baseline_kind == "prev_version"
        assert set(s.__dict__) == {
            "signal",
            "prompt_version",
            "model_name",
            "value",
            "baseline",
            "baseline_kind",
            "n_current",
            "n_baseline",
            "verdict",
        }


def test_emit_e_fail_open(monkeypatch, caplog):
    def _boom(db, ws):
        raise RuntimeError("db down")

    monkeypatch.setattr(mon, "compute_parecer_drift_signals", _boom)
    mon.emit_parecer_drift(db=None, workspace_id="ws1")  # não propaga


def test_stages_cobrem_legado_e_descritivo():
    assert set(mon.PARECER_STAGES) == {"review_finances_holistic", "E6-parecer"}
