"""Regressão: concordância singular/plural e pontuação dupla em top5_decisoes / s10.

Estende cobertura para imóveis (`s4`, `perfil_familia`) e riscos (`s9`):
todos compartilham o mesmo padrão `f"{n} <plural>"` que falhava em n=1.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pipeline.domain.services.narrativas import (
    ChartsNarrator,
    NarrativasContext,
    PerfilFamiliaNarrator,
    SummariesNarrator,
    ensure_period,
    pluralize,
)
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics


def _narrate_charts(decisoes: list[str]) -> dict[str, Any]:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    return ChartsNarrator(ctx).narrate(
        _build_metrics(),
        _FAMILY_BASE,
        [
            {"nome": "r1", "prob": "a", "impacto": "a"},
            {"nome": "r2", "prob": "a", "impacto": "a"},
            {"nome": "r3", "prob": "a", "impacto": "a"},
        ],
        decisoes,
    )


# ── top5_decisoes context: concordância singular/plural ────────────────


def test_top5_decisoes_context_singular_when_one_decisao():
    out = _narrate_charts(["Aporte mensal"])
    context = out["top5_decisoes"]["context"]
    assert "1 decisão estratégica" in context
    assert "1 decisões" not in context
    assert "decisões estratégicas" not in context


def test_top5_decisoes_context_plural_when_multiple_decisoes():
    out = _narrate_charts(["Aporte mensal", "CPA", "Holding"])
    context = out["top5_decisoes"]["context"]
    assert "3 decisões estratégicas" in context


def test_top5_decisoes_context_plural_when_zero_decisoes():
    out = _narrate_charts([])
    context = out["top5_decisoes"]["context"]
    assert "0 decisões estratégicas" in context


# ── top5_decisoes conclusion: sem ". ." ───────────────────────────────


def test_top5_decisoes_conclusion_no_double_period_when_one_decisao():
    out = _narrate_charts(["Aporte mensal"])
    conclusion = out["top5_decisoes"]["conclusion"]
    assert ". ." not in conclusion
    assert ".." not in conclusion
    assert conclusion.rstrip().endswith(".")
    assert not conclusion.rstrip().endswith("..")


def test_top5_decisoes_conclusion_no_double_period_when_many_decisoes():
    out = _narrate_charts(["d1", "d2", "d3", "d4", "d5"])
    conclusion = out["top5_decisoes"]["conclusion"]
    assert ". ." not in conclusion
    assert "Prioridade 2: d2" in conclusion
    assert conclusion.rstrip().endswith(".")
    assert not conclusion.rstrip().endswith("..")


def test_top5_decisoes_conclusion_strips_inline_periods_in_decisoes():
    """Itens de `decisoes[1:5]` já terminados em '.' não devem gerar '..'
    no meio do texto após o `". ".join(...)`. Reportado pelo product-designer
    review do PR original — `["d1.", "d2."]` produzia ".. " inline.
    """
    out = _narrate_charts(["d0", "Holding patrimonial.", "CPA expatriado.", "ITR."])
    conclusion = out["top5_decisoes"]["conclusion"]
    assert ".." not in conclusion
    assert "Prioridade 2: Holding patrimonial. " in conclusion
    assert "Prioridade 3: CPA expatriado" in conclusion
    assert "Prioridade 4: ITR." in conclusion


# ── summaries.s10 ──────────────────────────────────────────────────────


def test_summaries_s10_singular_when_one_decisao():
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    summaries = SummariesNarrator(ctx).narrate(
        _build_metrics(), _FAMILY_BASE, ["risco1"], ["Aporte mensal"]
    )
    s10 = summaries["s10"]
    assert "1 decisão estratégica prioritária" in s10
    assert "1 decisões" not in s10


def test_summaries_s10_plural_when_multiple_decisoes():
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    summaries = SummariesNarrator(ctx).narrate(
        _build_metrics(),
        _FAMILY_BASE,
        ["risco1"],
        ["d1", "d2", "d3", "d4"],
    )
    s10 = summaries["s10"]
    assert "4 decisões estratégicas prioritárias" in s10


# ── summaries.s4 (imóveis) ─────────────────────────────────────────────


def _narrate_summary(n_imoveis: int, riscos: list[str]) -> dict[str, str]:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = _build_metrics()
    metrics["n_imoveis"] = n_imoveis
    return SummariesNarrator(ctx).narrate(metrics, _FAMILY_BASE, riscos, ["Aporte"])


def test_summaries_s4_singular_when_one_imovel():
    s4 = _narrate_summary(1, ["risco1"])["s4"]
    assert "1 imóvel no portfólio" in s4
    assert "1 imóveis" not in s4


def test_summaries_s4_plural_when_multiple_imoveis():
    s4 = _narrate_summary(3, ["risco1"])["s4"]
    assert "3 imóveis no portfólio" in s4


# ── summaries.s9 (riscos) ──────────────────────────────────────────────


def test_summaries_s9_singular_when_one_risco():
    s9 = _narrate_summary(2, ["risco_unico"])["s9"]
    assert "1 risco prioritário" in s9
    assert "1 riscos" not in s9


def test_summaries_s9_plural_when_multiple_riscos():
    s9 = _narrate_summary(2, ["r1", "r2", "r3"])["s9"]
    assert "3 riscos prioritários" in s9


# ── perfil_familia (imóveis no <p>) ────────────────────────────────────


def _narrate_perfil(n_imoveis: int) -> dict[str, str]:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = _build_metrics()
    metrics["n_imoveis"] = n_imoveis
    return PerfilFamiliaNarrator(ctx).narrate(metrics, _FAMILY_BASE, today=date(2026, 4, 20))


def test_perfil_familia_singular_when_one_imovel():
    right = _narrate_perfil(1)["right"]
    assert "1 imóvel " in right
    assert "1 imóveis" not in right


def test_perfil_familia_plural_when_multiple_imoveis():
    right = _narrate_perfil(3)["right"]
    assert "3 imóveis " in right


# ── format_helpers unitários ───────────────────────────────────────────


def test_pluralize_singular_when_one():
    assert pluralize(1, "decisão", "decisões") == "decisão"


def test_pluralize_plural_when_zero():
    assert pluralize(0, "decisão", "decisões") == "decisões"


def test_pluralize_plural_when_many():
    assert pluralize(5, "decisão", "decisões") == "decisões"


def test_ensure_period_adds_when_missing():
    assert ensure_period("Foo") == "Foo."


def test_ensure_period_no_double_when_already_terminated():
    assert ensure_period("Foo.") == "Foo."
    assert ensure_period("Foo!") == "Foo!"
    assert ensure_period("Foo?") == "Foo?"


def test_ensure_period_handles_trailing_whitespace():
    assert ensure_period("Foo. ") == "Foo."
    assert ensure_period("Foo. \n") == "Foo."


def test_ensure_period_empty_string_returns_empty():
    assert ensure_period("") == ""
    assert ensure_period("   ") == ""


# Smoke import — `date` é usado implicitamente via `_build_metrics`
# (teste passa-se em ambiente sem freeze de tempo). Mantemos import
# explícito para manter parity com decomposition tests.
_ = date  # noqa: F841
