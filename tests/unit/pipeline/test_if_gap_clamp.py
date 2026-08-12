"""Regressão: `if_gap` clampado em 0 e sentinela não vira "0% declarado" (PR #1417)."""

# Os dois vêm da review `financial-planner` do fix de escala ×100. O gap negativo não
# ficava só no JSON: `summaries_narrator:283` e `charts_narrator:229,385,390` formatam
# como moeda em prosa, então a família lia "Gap de R$ −50,27 mi será fechado por
# aportes". `WaterfallIfChart.tsx:39` já clampava no fallback — o frontend estava mais
# correto que o domínio.

from datetime import date

import pytest

from pipeline.domain.services.if_projector import (
    IFProjector,
    IFProjectorConfig,
    default_if_absent,
)

_DOB = date(1982, 3, 1)


def _projector(if_meta: float) -> IFProjector:
    return IFProjector(
        IFProjectorConfig(
            if_meta=if_meta,
            if_trs_pct=4.0,
            titular_dob=_DOB,
            reference_date=date(2026, 8, 12),
        )
    )


def test_gap_clampado_quando_investivel_excede_a_meta():
    """`FORMULAS.md:26-27` manda MAX(0, ·) — gap negativo não existe no domínio."""
    proj = _projector(7_200_000.0).project(investivel=57_471_496.78)
    assert proj.if_gap == 0.0
    assert proj.if_pct > 100


def test_gap_positivo_preservado():
    proj = _projector(7_200_000.0).project(investivel=1_200_872.78)
    assert proj.if_gap == pytest.approx(5_999_127.22)


def test_gap_exatamente_zero_na_meta():
    assert _projector(1_000_000.0).project(investivel=1_000_000.0).if_gap == 0.0


class TestDefaultIfAbsent:
    """Sentinela de ausência ≠ zero declarado (ADR-373 D3)."""

    def test_sentinela_cai_no_default(self):
        """`ratios_calculator:156` emite "N/D"; virava r=0 → ramo *Sem trajetória*."""
        assert default_if_absent("N/D", 6.0) == 6.0

    def test_none_cai_no_default(self):
        assert default_if_absent(None, 6.0) == 6.0

    def test_zero_declarado_permanece_zero(self):
        """A família que escolheu não contar com o mercado declarou 0 — respeite."""
        assert default_if_absent(0, 6.0) == 0.0
        assert default_if_absent("0", 6.0) == 0.0

    def test_valor_declarado_vence_o_default(self):
        assert default_if_absent("7.5", 6.0) == pytest.approx(7.5)
        assert default_if_absent("7,5", 6.0) == pytest.approx(7.5)
