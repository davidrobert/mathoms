"""Regressão T01 (ADR-192) — empty state + has_us_exposure guard em S9 (charts + summaries)."""

from __future__ import annotations

from typing import Any

from pipeline.domain.services.narrativas import (
    ChartsNarrator,
    NarrativasContext,
    SummariesNarrator,
)
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics


def _narrate_charts_with(
    riscos: list[dict[str, Any]],
    decisoes: list[str] | None = None,
    *,
    metrics_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = _build_metrics()
    if metrics_overrides:
        metrics.update(metrics_overrides)
    return ChartsNarrator(ctx).narrate(
        metrics,
        _FAMILY_BASE,
        riscos,
        decisoes or ["d1"],
    )


def _narrate_summary_with(
    riscos_nomes: list[str],
    *,
    metrics_overrides: dict[str, Any] | None = None,
) -> str:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = _build_metrics()
    if metrics_overrides:
        metrics.update(metrics_overrides)
    summaries = SummariesNarrator(ctx).narrate(metrics, _FAMILY_BASE, riscos_nomes, ["Aporte"])
    return summaries["s9"]


# ── charts.bubble_riscos — empty state ──────────────────────────────────


def test_bubble_riscos_empty_list_uses_data_state_empty():
    out = _narrate_charts_with(riscos=[])
    bubble = out["bubble_riscos"]
    assert bubble["data_state"] == "empty"


def test_bubble_riscos_empty_list_no_broken_concatenation():
    """Sintoma original: ``"Riscos prioritários: . Ação: ..."`` (período colado
    em string vazia + range R$ 0-0M)."""
    out = _narrate_charts_with(riscos=[])
    bubble = out["bubble_riscos"]
    context, conclusion = bubble["context"], bubble["conclusion"]
    assert ": ." not in context
    assert ": ." not in conclusion
    assert "R$ 0-" not in context
    assert "R$ 0-" not in conclusion
    assert "R$ 0-0M" not in conclusion


def test_bubble_riscos_empty_list_no_us_assumption():
    """Empty default não pode mencionar CPA expatriado / FBAR / FATCA — não
    sabemos o perfil do workspace ainda."""
    out = _narrate_charts_with(riscos=[])
    bubble = out["bubble_riscos"]
    concat = bubble["context"] + " " + bubble["conclusion"]
    assert "CPA expatriado" not in concat
    assert "FBAR" not in concat
    assert "FATCA" not in concat


def test_bubble_riscos_populated_uses_data_state_ok():
    out = _narrate_charts_with(riscos=[{"nome": "morte", "prob": "alta", "impacto": "crítico"}])
    assert out["bubble_riscos"]["data_state"] == "ok"


# ── charts.bubble_riscos — has_us_exposure flag ─────────────────────────


def test_bubble_riscos_default_no_us_assumption_when_riscos_present():
    """Mesmo com riscos cadastrados, default (sem flag has_us_exposure)
    NÃO deve mencionar CPA expatriado."""
    out = _narrate_charts_with(
        riscos=[{"nome": "morte_provedor", "prob": "alta", "impacto": "crítico"}],
    )
    conclusion = out["bubble_riscos"]["conclusion"]
    assert "CPA expatriado" not in conclusion


def test_bubble_riscos_us_exposure_explicit_mentions_cpa():
    out = _narrate_charts_with(
        riscos=[{"nome": "fatca", "prob": "alta", "impacto": "alto"}],
        metrics_overrides={"has_us_exposure": True},
    )
    conclusion = out["bubble_riscos"]["conclusion"]
    assert "CPA expatriado" in conclusion


# ── charts.bubble_riscos — seguro_vida range degradação ─────────────────


def test_bubble_riscos_seguro_vida_zero_drops_range_and_falls_back():
    """Bag sem `seguro_vida_minimo/maximo` (ou ambos zero) não pode
    produzir ``R$ 0-0M``; cai para frase fallback de mitigação genérica."""
    out = _narrate_charts_with(
        riscos=[{"nome": "morte", "prob": "alta", "impacto": "crítico"}],
        metrics_overrides={"seguro_vida_minimo": 0, "seguro_vida_maximo": 0},
    )
    conclusion = out["bubble_riscos"]["conclusion"]
    assert "R$ 0-0M" not in conclusion
    assert "R$ 0-" not in conclusion
    # Fallback explícito quando não há range de cobertura calculado.
    assert "corretor habilitado" in conclusion


def test_bubble_riscos_seguro_vida_populated_keeps_range():
    out = _narrate_charts_with(
        riscos=[{"nome": "morte", "prob": "alta", "impacto": "crítico"}],
        metrics_overrides={"seguro_vida_minimo": 3_000_000, "seguro_vida_maximo": 5_000_000},
    )
    conclusion = out["bubble_riscos"]["conclusion"]
    assert "R$ 3-5M" in conclusion


# ── summaries.s9 — empty state ──────────────────────────────────────────


def test_summary_s9_empty_riscos_no_broken_concatenation():
    s9 = _narrate_summary_with(riscos_nomes=[])
    assert ": ." not in s9
    assert "R$ 0-0M" not in s9
    assert "0 riscos prioritários:" not in s9


def test_summary_s9_empty_riscos_mentions_console_cta():
    s9 = _narrate_summary_with(riscos_nomes=[])
    assert "Cadastr" in s9 or "Mape" in s9


def test_summary_s9_seguro_vida_zero_renders_a_definir():
    s9 = _narrate_summary_with(
        riscos_nomes=["r1", "r2"],
        metrics_overrides={"seguro_vida_minimo": 0, "seguro_vida_maximo": 0},
    )
    assert "R$ 0-0M" not in s9
    assert "a definir" in s9


def test_summary_s9_populated_keeps_format():
    s9 = _narrate_summary_with(
        riscos_nomes=["r1", "r2", "r3"],
        metrics_overrides={"seguro_vida_minimo": 3_000_000, "seguro_vida_maximo": 5_000_000},
    )
    assert "3 riscos prioritários" in s9
    assert "R$ 3-5M em seguro term" in s9
