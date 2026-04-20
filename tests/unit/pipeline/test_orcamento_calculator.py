"""Tests — ``OrcamentoProspectivoCalculator`` (Sessão A5a)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.orcamento_calculator import (  # noqa: E402
    OrcamentoProspectivo,
    OrcamentoProspectivoCalculator,
)


class TestCalculate:
    def test_divides_by_num_months(self):
        r = OrcamentoProspectivoCalculator().calculate(
            {"mercado": 1200, "uber": 360, "saude": 240},
            num_months=12,
        )

        assert r.categorias["mercado"] == pytest.approx(100.0)
        assert r.categorias["uber"] == pytest.approx(30.0)
        assert r.categorias["saude"] == pytest.approx(20.0)
        assert r.total == pytest.approx(150.0)
        assert r.media_mensal == pytest.approx(150.0)

    def test_zero_months_returns_empty(self):
        r = OrcamentoProspectivoCalculator().calculate(
            {"mercado": 1200}, num_months=0
        )

        assert r.categorias == {}
        assert r.total == 0.0
        assert "não disponível" in r.legenda

    def test_empty_dict_returns_zero_total(self):
        r = OrcamentoProspectivoCalculator().calculate({}, num_months=12)

        assert r.categorias == {}
        assert r.total == 0.0

    def test_legenda_mentions_num_months(self):
        r = OrcamentoProspectivoCalculator().calculate(
            {"mercado": 600}, num_months=6
        )

        assert "6 meses" in r.legenda

    def test_legacy_dict_rounds_values(self):
        r = OrcamentoProspectivoCalculator().calculate(
            {"cat": 100.123}, num_months=3
        )
        d = r.to_legacy_dict()

        assert d["categorias"]["cat"] == 33.37  # round(33.37099..., 2)

    def test_preserves_category_order(self):
        r = OrcamentoProspectivoCalculator().calculate(
            {"zebra": 60, "alpha": 60, "beta": 60}, num_months=12
        )

        # dict preserves insertion order.
        assert list(r.categorias.keys()) == ["zebra", "alpha", "beta"]


class TestResultType:
    def test_returns_orcamento_prospectivo(self):
        r = OrcamentoProspectivoCalculator().calculate({"m": 100}, num_months=10)
        assert isinstance(r, OrcamentoProspectivo)
