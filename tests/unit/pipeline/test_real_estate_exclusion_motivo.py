"""Todo imóvel excluído do investimento tem motivo redigido (ADR-215 enum · ADR-235)."""

# Fecha a CLASSE, não a instância: classification nova no enum sem motivo
# redigido cai no f-string genérico e vaza o nome cru do enum na tela do
# usuário ("Classification 'nu_proprietario' não é investimento.").

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app.models.property_identity import VALID_CLASSIFICATIONS
from pipeline.domain.services.real_estate_metrics import (
    _CLASSIFICATION_MOTIVO,
    INVESTMENT_CLASSIFICATIONS,
    BenchmarkRates,
    RealEstateConfig,
)
from pipeline.domain.services.real_estate_metrics_aggregator import compute_alertas

_BENCHMARKS = BenchmarkRates(
    cdi_liquido_pct=Decimal("9.0"),
    ntnb_liquido_pct=Decimal("6.0"),
    ifix_yield_pct=Decimal("8.0"),
    as_of_date=date(2026, 8, 11),
)

EXCLUDED_CLASSIFICATIONS = [c for c in VALID_CLASSIFICATIONS if c not in INVESTMENT_CLASSIFICATIONS]


@pytest.mark.parametrize("classification", EXCLUDED_CLASSIFICATIONS)
def test_classificacao_excluida_tem_motivo_redigido(classification):
    assert classification in _CLASSIFICATION_MOTIVO


@pytest.mark.parametrize("classification", EXCLUDED_CLASSIFICATIONS)
def test_motivo_nao_vaza_o_nome_do_enum(classification):
    motivo = _CLASSIFICATION_MOTIVO[classification]
    assert classification not in motivo
    assert motivo[0].isupper() and motivo.rstrip().endswith(".")


def test_classificacao_de_investimento_nao_precisa_de_motivo():
    """Motivo para classification de investimento seria inalcançável — não adicione."""
    for classification in INVESTMENT_CLASSIFICATIONS:
        assert classification not in _CLASSIFICATION_MOTIVO


# ADR-223: o opt-in de imóveis na IF pressupõe aluguel líquido acima da TRS.
class TestPremissaIfImoveis:
    def _alertas(self, cap_rate, imoveis_no_if):
        return compute_alertas(
            Decimal(cap_rate) if cap_rate is not None else None,
            Decimal("10.0"),
            _BENCHMARKS,
            [],
            RealEstateConfig(),
            imoveis_no_if,
        )

    def _codes(self, alertas):
        return {a.code for a in alertas}

    def test_dispara_quando_toggle_ligado_e_cap_rate_abaixo_da_premissa(self):
        assert "premissa_if_imoveis" in self._codes(self._alertas("1.35", True))

    def test_nao_dispara_com_toggle_desligado(self):
        assert "premissa_if_imoveis" not in self._codes(self._alertas("1.35", False))

    def test_nao_dispara_quando_cap_rate_atende_a_premissa(self):
        assert "premissa_if_imoveis" not in self._codes(self._alertas("3.0", True))

    def test_nao_dispara_sem_cap_rate(self):
        assert "premissa_if_imoveis" not in self._codes(self._alertas(None, True))

    def test_contexto_nao_manda_o_usuario_desligar_sozinho(self):
        alerta = [a for a in self._alertas("1.35", True) if a.code == "premissa_if_imoveis"][0]
        assert "Configurações" in alerta.context
        assert alerta.severity == "warning"
