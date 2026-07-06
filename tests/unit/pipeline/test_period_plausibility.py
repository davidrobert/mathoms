"""Tests — guardrail de plausibilidade de ano no período E3 (A28.l8).

Dogfood 72883bde produziu keys E3 com ano-fantasma: ``189912_190001``
(santander faturaunique, string bruta do parser) e ``210001``/``210006``
(c6bank faturacarbon, clamp de ``safe_date`` propagado via
``FATURA_DERIVED_FROM_TX_DATES``). Ano fora de [2015, 2035] nunca deve
expandir cego; sentinel oficial ``999999`` mantém passthrough legado.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.review_reason import ReviewReasonCode  # noqa: E402
from pipeline.domain.services.statement_preprocessor import (  # noqa: E402
    PeriodDerivationReason,
    StatementPeriodNormalizer,
)


def _conta(periodo: object | None = None, **extras) -> dict:
    base: dict = {"banco": "Itaú", "tipo": "extratoconta", "moeda": "BRL"}
    if periodo is not None:
        base["periodo"] = periodo
    base.update(extras)
    return base


def _fatura(**extras) -> dict:
    base: dict = {"banco": "Nubank", "tipo": "faturacarbon"}
    base.update(extras)
    return base


class TestPeriodoYearPlausibilityGuardrail:
    """Ano-fantasma (1899/2100) nunca vira artefato silencioso; sentinel 999999
    mantém o comportamento legado (passthrough para INVALID, sem needs_review).
    """

    def test_yyyymm_1899_skips_with_implausible_reason(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="189912")  # santander faturaunique (dogfood 72883bde)

        result = normalizer.normalize(data, source_name="santander_faturaunique.json")

        assert result.skip is True
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE
        assert result.warnings[0].raw_value == "189912"

    def test_yyyymm_2100_skips_with_implausible_reason(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="210001")  # c6bank faturacarbon (clamp de safe_date)

        result = normalizer.normalize(data)

        assert result.skip is True
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE

    def test_sentinel_999999_passthrough_never_implausible(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="999999")  # sentinel oficial (CLAUDE.md §naming)

        result = normalizer.normalize(data)

        assert result.skip is False  # comportamento legado preservado
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_STRING_INVALID
        review = result.warnings[0].to_review_reason(
            stage="reconcile_transactions", artifact_key="k", document_id=None
        )
        assert review is None

    def test_boundary_years_2015_and_2035_expand_normally(self) -> None:
        normalizer = StatementPeriodNormalizer()

        for periodo in ("201501", "203512"):
            result = normalizer.normalize(_conta(periodo=periodo))
            assert result.skip is False
            assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_STRING_YYYYMM

    def test_iso_date_with_implausible_year_skips(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="1899-12-30")

        result = normalizer.normalize(data)

        assert result.skip is True
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE

    def test_flat_fields_with_implausible_year_skip(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta()
        data["periodo_inicio"] = "2100-01-01"
        data["periodo_fim"] = "2100-06-30"

        result = normalizer.normalize(data)

        assert result.skip is True
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE

    def test_periodo_dict_with_implausible_year_skips(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo={"inicio": "1899-12-01", "fim": "1900-01-31"})

        result = normalizer.normalize(data)

        assert result.skip is True
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE

    def test_fatura_synthesis_from_clamped_tx_dates_skips(self) -> None:
        # c6 carbon: datas clampadas a 2100 por safe_date propagavam via
        # FATURA_DERIVED_FROM_TX_DATES e viravam key 210001/210006.
        normalizer = StatementPeriodNormalizer()
        data = _fatura(
            transacoes=[
                {"data": "2100-01-05", "descricao": "compra", "valor": -10.0},
                {"data": "2100-06-01", "descricao": "compra", "valor": -20.0},
            ]
        )

        result = normalizer.normalize(data)

        assert result.skip is True
        reasons = [w.reason for w in result.warnings]
        assert PeriodDerivationReason.PERIODO_YEAR_IMPLAUSIBLE in reasons

    def test_implausible_warning_projects_to_review_reason(self) -> None:
        normalizer = StatementPeriodNormalizer()
        result = normalizer.normalize(_conta(periodo="210001"), source_name="src.json")

        review = result.warnings[0].to_review_reason(
            stage="reconcile_transactions", artifact_key="src", document_id=None
        )

        assert review is not None
        assert review.code is ReviewReasonCode.dedup_sentinel_period
        assert "210001" in review.offending_value
        assert "2015" in review.expected and "2035" in review.expected
