"""Tests para constructors typed dos analyzers (A7.2b · ADR-135)."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.cenarios_conjuge_analyzer import (  # noqa: E402
    CenariosConjugeConfig,
)
from pipeline.domain.services.previdencia_analyzer import (  # noqa: E402
    PrevidenciaConfig,
)
from pipeline.domain.types.config import FiscalParameters, IRPFBracket  # noqa: E402

_DAVID_DOB = date(1985, 6, 12)


def _fiscal_2025() -> FiscalParameters:
    return FiscalParameters(
        year=2025,
        pgbl_limit_brl_cents=0,
        inss_ceiling_brl_cents=0,
        lucro_presumido_aliquota=Decimal("0.32"),
        ir_brackets=(
            IRPFBracket(upper_brl_cents=2696320, aliquota_pct=Decimal("0.0"), deducao_brl_cents=0),
            IRPFBracket(upper_brl_cents=None, aliquota_pct=Decimal("27.5"), deducao_brl_cents=0),
        ),
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 12, 31),
        source="test",
    )


# ---------------------------------------------------------------------------
# PrevidenciaConfig.from_fiscal_parameters
# ---------------------------------------------------------------------------


class TestPrevidenciaFromFiscalParameters:
    def test_lucro_presumido_pct_x100_decimal_to_pct(self):
        cfg = PrevidenciaConfig.from_fiscal_parameters(_fiscal_2025())
        # DB armazena 0.32 (DECIMAL); analyzer trabalha em pct (32.0)
        assert cfg.lucro_presumido_pct == 32.0

    def test_brackets_converted_with_correct_units(self):
        cfg = PrevidenciaConfig.from_fiscal_parameters(_fiscal_2025())
        # 2696320 cents → 26963.20 R$ anual
        assert cfg.irpf_faixas[0].limite_anual == 26963.20
        assert cfg.irpf_faixas[0].aliquota_pct == 0.0
        assert cfg.irpf_faixas[-1].limite_anual is None
        assert cfg.irpf_faixas[-1].aliquota_pct == 27.5

    def test_default_pgbl_pct_when_db_has_zero(self):
        cfg = PrevidenciaConfig.from_fiscal_parameters(_fiscal_2025())
        # Seed coloca 0 cents (sentinel); usa default 12% conforme ADR-135.
        assert cfg.pgbl_limite_pct == 12.0

    def test_lucro_presumido_falls_back_to_32_when_db_zero(self):
        empty = FiscalParameters(year=2025, lucro_presumido_aliquota=Decimal("0"))
        cfg = PrevidenciaConfig.from_fiscal_parameters(empty)
        assert cfg.lucro_presumido_pct == 32.0

    def test_legacy_from_fiscal_dict_still_works(self):
        """Não quebrar fallback dict-based durante cutover."""
        cfg = PrevidenciaConfig.from_fiscal({"lucro_presumido": {"percentual_servicos_pct": 32.0}})
        assert cfg.lucro_presumido_pct == 32.0


# ---------------------------------------------------------------------------
# CenariosConjugeConfig — A7.2b typed cambio removido em A8.4 PR2 (ADR-167):
# analyzer não depende mais de USD/cambio, só de aporte_base/fator_reduzido.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# E5N — _resolve_cambio_via_config_store (A7.5)
# ---------------------------------------------------------------------------


class TestE5NResolveCambioViaConfigStore:
    def test_returns_none_when_ctx_is_none(self):
        from scripts.e5n_narrativas import _resolve_cambio_via_config_store

        assert _resolve_cambio_via_config_store(None) is None

    def test_returns_none_when_ctx_lacks_config_store(self):
        from scripts.e5n_narrativas import _resolve_cambio_via_config_store

        class _Ctx:
            pass

        assert _resolve_cambio_via_config_store(_Ctx()) is None

    def test_returns_decimal_from_config_store(self):
        from scripts.e5n_narrativas import _resolve_cambio_via_config_store

        class _CS:
            def get_market_rate(self, pair: str, observed_at) -> Decimal:
                assert pair == "USD/BRL"
                return Decimal("6.10")

        class _Ctx:
            config_store = _CS()

        rate = _resolve_cambio_via_config_store(_Ctx())
        assert rate == Decimal("6.10")

    def test_returns_none_on_config_store_exception(self):
        from scripts.e5n_narrativas import _resolve_cambio_via_config_store

        class _CS:
            def get_market_rate(self, pair: str, observed_at) -> Decimal:
                raise KeyError("USD/BRL not seeded")

        class _Ctx:
            config_store = _CS()

        assert _resolve_cambio_via_config_store(_Ctx()) is None


class TestE5NLoadMetricsTypedCambio:
    """A7.5: ``load_metrics_from_e5(cambio_usd_brl=...)`` override."""

    def test_typed_cambio_overrides_taxas_json(self, tmp_path, monkeypatch):
        """Decimal passado via kwarg substitui valor de taxas.json em METRICS."""
        import scripts.e5n_narrativas as e5n

        e5n._init_config(tmp_path)
        monkeypatch.setattr(e5n, "_load_taxas", lambda: {"cambio_usd_brl": 5.0})

        e5_data = {
            "patrimonio": {},
            "goals": {},
            "fluxo_caixa": {},
            "ratios": {},
            "score": {},
            "reserva_emergencia": {},
        }
        metrics = e5n.load_metrics_from_e5(e5_data, cambio_usd_brl=Decimal("6.50"))
        assert metrics["cambio_usd_brl"] == 6.50

    def test_taxas_json_used_when_typed_none(self, tmp_path, monkeypatch):
        import scripts.e5n_narrativas as e5n

        e5n._init_config(tmp_path)
        monkeypatch.setattr(e5n, "_load_taxas", lambda: {"cambio_usd_brl": 5.0})

        e5_data = {
            "patrimonio": {},
            "goals": {},
            "fluxo_caixa": {},
            "ratios": {},
            "score": {},
            "reserva_emergencia": {},
        }
        metrics = e5n.load_metrics_from_e5(e5_data)
        assert metrics["cambio_usd_brl"] == 5.0
