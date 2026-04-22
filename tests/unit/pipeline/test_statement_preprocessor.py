"""Tests — ``StatementPeriodNormalizer`` e ``AnachronicTransactionDropper``
(Fase 6 foundation · Sessão A1).

Cobre paridade comportamental com ``scripts/e3_reconcile.py:655-795``:
- normalização de ``periodo`` string (YYYYMM, YYYY-MM-DD, inválido)
- síntese de ``periodo`` para faturas (chain de fallbacks)
- ajuste de ``inicio`` para min(tx_dates) — fix #4 do legado
- guard anachronic (>180 dias antes de ``periodo.inicio``)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.statement_preprocessor import (  # noqa: E402
    AnachronicFilterResult,
    AnachronicGuardConfig,
    AnachronicTransactionDropper,
    AnachronicTransactionWarning,
    NormalizationResult,
    PeriodDerivationReason,
    PeriodDerivationWarning,
    StatementPeriodNormalizer,
)

# =============================================================================
# Helpers
# =============================================================================


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


# =============================================================================
# StatementPeriodNormalizer — case 1: periodo já é dict
# =============================================================================


class TestSchemaOfficialFormat:
    """Caso 0: ``periodo_inicio``/``periodo_fim`` (formato do JSON Schema E2).

    O normalizer deve aceitar esse formato sem warnings nem mutações — é o
    output dos parsers de ``scripts/e2/banks/``.
    """

    def test_periodo_inicio_fim_returns_unchanged(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = {
            "banco": "Itaú",
            "tipo": "extratoconta",
            "periodo_inicio": "2025-01-01",
            "periodo_fim": "2025-01-31",
            "transacoes": [],
        }

        result = normalizer.normalize(data)

        assert result.skip is False
        assert result.warnings == ()
        assert result.data["periodo_inicio"] == "2025-01-01"
        assert result.data["periodo_fim"] == "2025-01-31"


class TestPeriodoAlreadyDict:
    def test_periodo_dict_returns_unchanged_no_warnings(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo={"inicio": "2025-01-01", "fim": "2025-01-31"})

        result = normalizer.normalize(data)

        assert isinstance(result, NormalizationResult)
        assert result.skip is False
        assert result.warnings == ()
        assert result.data["periodo"] == {"inicio": "2025-01-01", "fim": "2025-01-31"}

    def test_does_not_mutate_input(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo={"inicio": "2025-01-01", "fim": "2025-01-31"})

        result = normalizer.normalize(data)
        result.data["periodo"]["inicio"] = "1999-01-01"

        assert data["periodo"]["inicio"] == "2025-01-01"


# =============================================================================
# StatementPeriodNormalizer — case 2: periodo é string
# =============================================================================


class TestPeriodoString:
    def test_yyyymm_expands_to_full_month(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="202501")

        result = normalizer.normalize(data, source_name="src.json")

        assert result.skip is False
        assert result.data["periodo"] == {
            "inicio": "2025-01-01",
            "fim": "2025-01-31",
        }
        assert len(result.warnings) == 1
        w = result.warnings[0]
        assert w.reason == PeriodDerivationReason.PERIODO_STRING_YYYYMM
        assert w.source == "src.json"
        assert w.derived_inicio == "2025-01-01"
        assert w.derived_fim == "2025-01-31"
        assert w.raw_value == "202501"

    def test_yyyymm_february_handles_leap_year(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="202402")  # 2024 é bissexto

        result = normalizer.normalize(data)

        assert result.data["periodo"]["fim"] == "2024-02-29"

    def test_iso_date_expands_to_single_day(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="2025-03-15")

        result = normalizer.normalize(data)

        assert result.data["periodo"] == {"inicio": "2025-03-15", "fim": "2025-03-15"}
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_STRING_DATE

    def test_invalid_string_yields_empty_periodo(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="garbage")

        result = normalizer.normalize(data)

        assert result.skip is False  # legado também não pula
        assert result.data["periodo"] == {"inicio": "", "fim": ""}
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_STRING_INVALID

    def test_yyyymm_with_invalid_month_falls_back_to_invalid(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta(periodo="202513")  # mês 13

        result = normalizer.normalize(data)

        assert result.data["periodo"] == {"inicio": "", "fim": ""}
        assert result.warnings[0].reason == PeriodDerivationReason.PERIODO_STRING_INVALID


# =============================================================================
# StatementPeriodNormalizer — case 3: extratos não-fatura sem periodo
# =============================================================================


class TestNonFaturaWithoutPeriodo:
    def test_extrato_without_periodo_skips(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _conta()  # sem periodo

        result = normalizer.normalize(data)

        assert result.skip is True
        assert result.warnings == ()


# =============================================================================
# StatementPeriodNormalizer — case 4: faturas sem periodo
# =============================================================================


class TestFaturaSynthesis:
    def test_fatura_with_data_vencimento_synthesizes_30d_window(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _fatura(data_vencimento="2025-04-15", transacoes=[])

        result = normalizer.normalize(data, source_name="fat.json")

        assert result.skip is False
        # 2025-04-15 - 30 dias = 2025-03-16
        assert result.data["periodo"] == {
            "inicio": "2025-03-16",
            "fim": "2025-04-15",
        }
        reasons = [w.reason for w in result.warnings]
        assert PeriodDerivationReason.FATURA_DERIVED_FROM_DATA_VENCIMENTO in reasons

    def test_fatura_inicio_adjusted_when_tx_predates_synth(self) -> None:
        """Fix #4 do legado: se min(tx_dates) < synth_inicio, ajusta para min."""
        normalizer = StatementPeriodNormalizer()
        data = _fatura(
            data_vencimento="2025-04-15",
            transacoes=[
                {"data": "2025-03-01", "descricao": "Compra", "valor": -50.0},
                {"data": "2025-04-10", "descricao": "Compra2", "valor": -30.0},
            ],
        )

        result = normalizer.normalize(data, source_name="fat.json")

        assert result.data["periodo"]["inicio"] == "2025-03-01"
        assert result.data["periodo"]["fim"] == "2025-04-15"
        reasons = [w.reason for w in result.warnings]
        assert PeriodDerivationReason.FATURA_INICIO_ADJUSTED_TO_TX in reasons

    def test_fatura_inicio_not_adjusted_when_tx_within_window(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _fatura(
            data_vencimento="2025-04-15",
            transacoes=[
                {"data": "2025-04-01", "descricao": "Compra", "valor": -50.0},
            ],
        )

        result = normalizer.normalize(data)

        assert result.data["periodo"]["inicio"] == "2025-03-16"
        reasons = [w.reason for w in result.warnings]
        assert PeriodDerivationReason.FATURA_INICIO_ADJUSTED_TO_TX not in reasons

    def test_fatura_without_data_vencimento_with_txns_derives_from_tx(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _fatura(
            transacoes=[
                {"data": "2025-04-01", "descricao": "C", "valor": -10.0},
                {"data": "2025-04-20", "descricao": "C", "valor": -20.0},
                {"data": "2025-04-10", "descricao": "C", "valor": -30.0},
            ],
        )

        result = normalizer.normalize(data, source_name="fat.json")

        assert result.skip is False
        assert result.data["periodo"] == {
            "inicio": "2025-04-01",
            "fim": "2025-04-20",
        }
        assert result.warnings[0].reason == PeriodDerivationReason.FATURA_DERIVED_FROM_TX_DATES

    def test_fatura_without_data_vencimento_and_no_txns_skips(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _fatura(transacoes=[])

        result = normalizer.normalize(data)

        assert result.skip is True
        assert (
            result.warnings[0].reason
            == PeriodDerivationReason.FATURA_NO_PERIODO_NO_DATA_VENCIMENTO_NO_TXNS
        )

    def test_fatura_with_invalid_data_vencimento_falls_back_to_tx_dates(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _fatura(
            data_vencimento="not-a-date",
            transacoes=[
                {"data": "2025-04-05", "descricao": "C", "valor": -10.0},
                {"data": "2025-04-15", "descricao": "C", "valor": -20.0},
            ],
        )

        result = normalizer.normalize(data)

        assert result.skip is False
        assert result.data["periodo"] == {"inicio": "2025-04-05", "fim": "2025-04-15"}
        assert result.warnings[0].reason == PeriodDerivationReason.FATURA_DERIVED_FROM_TX_DATES

    def test_fatura_with_invalid_data_vencimento_and_no_txns_skips(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _fatura(data_vencimento="bad", transacoes=[])

        result = normalizer.normalize(data)

        assert result.skip is True

    def test_fatura_synthesis_propagates_saldo_from_anterior_atual(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _fatura(
            data_vencimento="2025-04-15",
            saldo_anterior=100.0,
            saldo_atual=200.0,
            transacoes=[],
        )

        result = normalizer.normalize(data)

        assert result.data["saldo_inicial"] == 100.0
        assert result.data["saldo_final"] == 200.0

    def test_fatura_with_existing_saldos_does_not_overwrite(self) -> None:
        normalizer = StatementPeriodNormalizer()
        data = _fatura(
            data_vencimento="2025-04-15",
            saldo_anterior=100.0,
            saldo_atual=200.0,
            saldo_inicial=999.0,  # já existe
            saldo_final=888.0,
            transacoes=[],
        )

        result = normalizer.normalize(data)

        assert result.data["saldo_inicial"] == 999.0
        assert result.data["saldo_final"] == 888.0


# =============================================================================
# AnachronicTransactionDropper
# =============================================================================


class TestAnachronicGuard:
    def test_no_dropped_when_all_within_window(self) -> None:
        dropper = AnachronicTransactionDropper()
        data = {
            "periodo": {"inicio": "2025-04-01", "fim": "2025-04-30"},
            "transacoes": [
                {"data": "2025-04-05", "valor": -10.0},
                {"data": "2025-04-15", "valor": -20.0},
            ],
        }

        result = dropper.filter(data)

        assert isinstance(result, AnachronicFilterResult)
        assert result.warning is None
        assert len(result.data["transacoes"]) == 2

    def test_drops_transactions_older_than_180_days(self) -> None:
        dropper = AnachronicTransactionDropper()
        data = {
            "periodo": {"inicio": "2025-04-01", "fim": "2025-04-30"},
            "transacoes": [
                {"data": "2024-09-01", "valor": -100.0},  # >180d antes
                {"data": "2025-04-05", "valor": -10.0},
            ],
        }

        result = dropper.filter(data, source_name="src.json")

        assert isinstance(result.warning, AnachronicTransactionWarning)
        assert result.warning.dropped_count == 1
        assert result.warning.source == "src.json"
        assert result.warning.periodo_inicio == "2025-04-01"
        # 2025-04-01 - 180d = 2024-10-03
        assert result.warning.cutoff == "2024-10-03"
        assert len(result.data["transacoes"]) == 1
        assert result.data["transacoes"][0]["data"] == "2025-04-05"

    def test_keeps_transactions_inside_180d_window(self) -> None:
        dropper = AnachronicTransactionDropper()
        data = {
            "periodo": {"inicio": "2025-04-01", "fim": "2025-04-30"},
            "transacoes": [
                # 2024-11-15 está dentro de 180d (cutoff = 2024-10-03)
                {"data": "2024-11-15", "valor": -50.0},
                {"data": "2025-04-05", "valor": -10.0},
            ],
        }

        result = dropper.filter(data)

        assert result.warning is None
        assert len(result.data["transacoes"]) == 2

    def test_no_periodo_skips_filter(self) -> None:
        dropper = AnachronicTransactionDropper()
        data = {
            "periodo": {"inicio": "", "fim": ""},
            "transacoes": [{"data": "2020-01-01", "valor": -10.0}],
        }

        result = dropper.filter(data)

        assert result.warning is None
        assert len(result.data["transacoes"]) == 1

    def test_invalid_periodo_inicio_skips_filter(self) -> None:
        dropper = AnachronicTransactionDropper()
        data = {
            "periodo": {"inicio": "garbage", "fim": ""},
            "transacoes": [{"data": "2020-01-01", "valor": -10.0}],
        }

        result = dropper.filter(data)

        assert result.warning is None
        assert len(result.data["transacoes"]) == 1

    def test_custom_window_size(self) -> None:
        dropper = AnachronicTransactionDropper(
            AnachronicGuardConfig(max_days_before_periodo_inicio=30)
        )
        data = {
            "periodo": {"inicio": "2025-04-01", "fim": "2025-04-30"},
            "transacoes": [
                {"data": "2025-02-15", "valor": -10.0},  # 45d antes — fora
                {"data": "2025-03-15", "valor": -20.0},  # 17d antes — dentro
            ],
        }

        result = dropper.filter(data)

        assert result.warning is not None
        assert result.warning.dropped_count == 1
        assert len(result.data["transacoes"]) == 1
        assert result.data["transacoes"][0]["data"] == "2025-03-15"

    def test_does_not_mutate_input(self) -> None:
        dropper = AnachronicTransactionDropper()
        data = {
            "periodo": {"inicio": "2025-04-01", "fim": "2025-04-30"},
            "transacoes": [
                {"data": "2024-09-01", "valor": -100.0},
                {"data": "2025-04-05", "valor": -10.0},
            ],
        }

        dropper.filter(data)

        assert len(data["transacoes"]) == 2

    def test_supports_flat_periodo_inicio_field(self) -> None:
        """Schema oficial do E2 usa ``periodo_inicio``/``periodo_fim`` planos —
        dropper deve aceitar esse formato também."""
        dropper = AnachronicTransactionDropper()
        data = {
            "periodo_inicio": "2025-04-01",
            "periodo_fim": "2025-04-30",
            "transacoes": [
                {"data": "2024-09-01", "valor": -100.0},
                {"data": "2025-04-05", "valor": -10.0},
            ],
        }

        result = dropper.filter(data)

        assert result.warning is not None
        assert result.warning.dropped_count == 1
        assert len(result.data["transacoes"]) == 1

    def test_warning_format_is_useful(self) -> None:
        warning = AnachronicTransactionWarning(
            source="extrato.json",
            periodo_inicio="2025-04-01",
            cutoff="2024-10-03",
            dropped_count=2,
            sample_dates=("2024-08-15", "2024-09-01"),
        )

        formatted = warning.format()

        assert "extrato.json" in formatted
        assert "2025-04-01" in formatted
        assert "dropped=2" in formatted

    def test_period_warning_format_is_useful(self) -> None:
        warning = PeriodDerivationWarning(
            source="fat.json",
            reason=PeriodDerivationReason.FATURA_DERIVED_FROM_DATA_VENCIMENTO,
            derived_inicio="2025-03-16",
            derived_fim="2025-04-15",
            raw_value="2025-04-15",
        )

        formatted = warning.format()

        assert "fat.json" in formatted
        assert "2025-03-16" in formatted
        assert "2025-04-15" in formatted
