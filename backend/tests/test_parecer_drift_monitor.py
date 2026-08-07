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


# ----------------------------------------------------------------------
# A40.l30 item 4 — ancoragem sobre `pipeline_stage_logs.output_summary`
# ----------------------------------------------------------------------


# `itens=19` e `ancoras=9` são os valores MEDIDOS em produção (66 execuções reais,
# `dev/measure_parecer_ancoragem.py`), não o denominador ~7 do golden sintético. Testar
# com 7 calibraria o piso na régua errada — foi o que a re-medição refutou.
def _summary(
    *, prompt: str, manifest: str, itens=19, ancoras=9, prosa=0, instrumentado: bool = True
) -> dict:
    """`output_summary` do stage. `instrumentado=False` omite `itens_total` — é a forma
    que um cache hit pré-A40.l30 PR1 serve (ADR-366 §D7 guarda o summary no envelope)."""
    verification = {
        "prompt_version": prompt,
        "ancoras_total": ancoras,
        "money_tokens_total": prosa,
    }
    if instrumentado:
        verification["itens_total"] = itens
        verification["prose_inventory_version"] = 2
    return {"manifest_version": manifest, "evidencia_verification": verification}


def _anchor_signals(monkeypatch, summaries):
    monkeypatch.setattr(mon, "_fetch_parecer_stage_summaries", lambda db, ws: summaries)
    return _by_name(mon.compute_ancoragem_drift_signals(db=None, workspace_id="ws1"))


def test_a_regressao_real_do_1004_dispara_warn(monkeypatch):
    """O caso que o sinal existe para pegar, com os números REAIS: 9→5 âncoras sobre
    ~19 itens ⇒ Δ = −0,211/item, acima do piso 0,15. Com o piso 0,30 da estimativa
    inicial (denominador ~7 do golden) este teste ficaria VERDE com a regressão viva."""
    atual = [_summary(prompt="2.2.0", manifest="2.0.2", ancoras=5)] * 10
    base = [_summary(prompt="2.1.0", manifest="1.8", ancoras=9)] * 10
    by = _anchor_signals(monkeypatch, atual + base)
    assert by["ancoras_por_item_delta"].verdict == "warn"
    assert by["ancoras_por_item_delta"].value == pytest.approx(-0.2105, abs=1e-3)
    assert abs(by["ancoras_por_item_delta"].value) > mon.ANCORAS_POR_ITEM_FLOOR


def test_variacao_de_uma_ancora_nao_dispara(monkeypatch):
    """Ruído de 1 âncora em 19 itens (Δ ≈ 0,05) fica dentro da banda."""
    atual = [_summary(prompt="2.2.0", manifest="2.0.2", ancoras=8)] * 10
    base = [_summary(prompt="2.1.0", manifest="2.0.2", ancoras=9)] * 10
    assert _anchor_signals(monkeypatch, atual + base)["ancoras_por_item_delta"].verdict == "ok"


def test_prosa_monetaria_por_item_dispara_warn(monkeypatch):
    """Medido: 0,000 → 0,190 token/item entre 2.1.0/1.8 e 2.2.0/2.0.2 (≈ 3,6 tokens
    sobre 19 itens), acima do piso 0,10."""
    atual = [_summary(prompt="2.2.0", manifest="2.0.2", prosa=4)] * 10
    base = [_summary(prompt="2.1.0", manifest="1.8", prosa=0)] * 10
    by = _anchor_signals(monkeypatch, atual + base)
    assert by["prosa_monetaria_rate_delta"].verdict == "warn"
    assert by["prosa_monetaria_rate_delta"].baseline == pytest.approx(0.0)
    assert by["prosa_monetaria_rate_delta"].value == pytest.approx(0.2105, abs=1e-3)


def test_summary_sem_itens_total_e_unknown_e_nunca_zero(monkeypatch):
    """O invariante de leitura da lane: ausência da chave é `unknown`, jamais 0. Lida
    como 0, a janela pré-instrumento produziria densidade 0 e um delta de drift falso."""
    atual = [_summary(prompt="2.2.0", manifest="2.0.2", instrumentado=False)] * 10
    base = [_summary(prompt="2.1.0", manifest="1.9", ancoras=9)] * 10
    by = _anchor_signals(monkeypatch, atual + base)
    assert "ancoras_por_item_delta" not in by  # não computa delta contra o desconhecido
    sample = by["ancoragem_window_sample"]
    assert sample.verdict == "insufficient_data:unknown=10"
    assert sample.n_current == 0


def test_itens_total_zero_nao_divide(monkeypatch):
    """Parecer sem risco nem sugestão: denominador 0 não é taxa — row é descartada."""
    atual = [_summary(prompt="2.2.0", manifest="2.0.2", itens=0)] * 10
    base = [_summary(prompt="2.1.0", manifest="1.9", ancoras=9)] * 10
    assert _anchor_signals(monkeypatch, atual + base)["ancoragem_window_sample"].n_current == 0


def test_manifest_version_estratifica_junto_com_prompt_version(monkeypatch):
    """O confounder que a lane nomeia: mesma `prompt_version`, manifest diferente ⇒
    janelas diferentes. Sem isso, drift de payload (#1006/#1010) entra como drift de
    prompt."""
    atual = [_summary(prompt="2.2.0", manifest="2.0.2", ancoras=5)] * 10
    base = [_summary(prompt="2.2.0", manifest="1.9", ancoras=9)] * 10
    by = _anchor_signals(monkeypatch, atual + base)
    assert by["ancoras_por_item_delta"].verdict == "warn"
    assert by["ancoras_por_item_delta"].model_name == "manifest=2.0.2"


def test_sem_summary_retorna_vazio(monkeypatch):
    assert _anchor_signals(monkeypatch, []) == {}
