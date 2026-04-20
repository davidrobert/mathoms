"""Tests — ``RatiosCalculator`` (Sessão A5a)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.ratios_calculator import (  # noqa: E402
    FinancialRatios,
    RatiosCalculator,
)


def _fluxo_with_janela(
    *,
    receita_recorrente: float = 120_000,
    receita_total: float = 130_000,
    despesa_total: float = 60_000,
    despesa_mensal_media: float = 5_000,
    periodo: str = "2025-04 a 2026-03",
    n_meses: int = 12,
) -> dict:
    return {
        "janela_12m": {
            "receita_recorrente": receita_recorrente,
            "receita_total": receita_total,
            "despesa_total": despesa_total,
            "despesa_mensal_media": despesa_mensal_media,
            "periodo": periodo,
            "n_meses": n_meses,
        }
    }


def _patrimonio(bruto: float = 1_000_000, dividas: float = 200_000, investivel: float = 500_000) -> dict:
    return {"bruto": bruto, "dividas": dividas, "investivel": investivel}


class TestTaxaPoupanca:
    def test_recorrente_when_janela_present(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(receita_recorrente=100_000, despesa_total=50_000),
            _patrimonio(),
        )
        # (100k - 50k) / 100k = 50%
        assert r.taxa_poupanca_recorrente_pct == pytest.approx(50.0)

    def test_total_uses_receita_total_not_recorrente(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(receita_recorrente=100_000, receita_total=120_000, despesa_total=60_000),
            _patrimonio(),
        )
        # (120k - 60k) / 120k = 50%
        assert r.taxa_poupanca_total_pct == pytest.approx(50.0)

    def test_zero_when_receita_zero(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(receita_recorrente=0, receita_total=0),
            _patrimonio(),
        )
        assert r.taxa_poupanca_recorrente_pct == 0.0
        assert r.taxa_poupanca_total_pct == 0.0


class TestEndividamento:
    def test_percentual_do_bruto(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(),
            _patrimonio(bruto=1_000_000, dividas=200_000),
        )
        assert r.taxa_endividamento_pct == pytest.approx(20.0)

    def test_zero_when_bruto_zero(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(),
            _patrimonio(bruto=0),
        )
        assert r.taxa_endividamento_pct == 0.0


class TestCobertura:
    def test_cobertura_meses(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_media=5_000),
            _patrimonio(investivel=60_000),
        )
        assert r.cobertura_despesas_meses == pytest.approx(12.0)

    def test_zero_when_despesa_zero(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_media=0),
            _patrimonio(),
        )
        assert r.cobertura_despesas_meses == 0.0


class TestJanela:
    def test_uses_janela_12m_when_present(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(periodo="2025-04 a 2026-03", n_meses=12),
            _patrimonio(),
        )
        assert r.janela_referencia == "2025-04 a 2026-03"
        assert r.janela_n_meses == 12

    def test_falls_back_to_periodo_completo_when_janela_absent(self):
        fluxo = {
            "receita_recorrente": 100_000,
            "receita_total": 100_000,
            "despesa_total": 50_000,
            "despesa_mensal_media": 4_000,
        }
        r = RatiosCalculator().calculate(fluxo, _patrimonio())

        assert r.janela_referencia == "período completo"
        assert r.janela_n_meses == 0


class TestPlaceholders:
    def test_rentabilidade_and_ir_are_nd(self):
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())

        assert r.rentabilidade_pct == "N/D"
        assert r.aliquota_efetiva_ir_pct == "N/D"


class TestLegacyDict:
    def test_has_all_expected_fields(self):
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())
        d = r.to_legacy_dict()

        required = {
            "taxa_poupanca_recorrente_pct",
            "taxa_poupanca_total_pct",
            "taxa_endividamento_pct",
            "cobertura_despesas_meses",
            "rentabilidade_pct",
            "aliquota_efetiva_ir_pct",
            "janela_referencia",
            "janela_n_meses",
        }
        assert required.issubset(d.keys())
