"""Tests — redutor da Lei 15.270/2025 ([[ADR-414]] D3).

Coeficientes conferidos em fonte primária (RFB, orientação de dez/2025) pelo
co-design de 2026-08-24: banda anual `8.429,73 − 0,095575 × bruto`, zero acima de
R$ 88.200.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.irpf_redutor import redutor_devido  # noqa: E402
from pipeline.domain.types.config import RedutorIRPF  # noqa: E402

ANUAL_2026 = RedutorIRPF(
    piso_bruto_brl_cents=6_000_000,
    teto_bruto_brl_cents=8_820_000,
    intercepto_brl_cents=842_973,
    coeficiente=Decimal("0.095575"),
    vigencia_ref="Lei 15.270/2025, ajuste anual a partir do exercício 2027 (AC2026)",
    source="RFB — orientação de 2025-12",
)

_c = lambda reais: int(Decimal(reais) * 100)  # noqa: E731


class TestBandas:
    def test_acima_do_teto_nao_reduz(self):
        assert redutor_devido(_c("95000"), _c("10000"), ANUAL_2026) == 0

    def test_banda_2_segue_a_reta_da_norma(self):
        """70.000 → 8.429,73 − 0,095575 × 70.000 = 1.739,48."""
        assert redutor_devido(_c("70000"), _c("99999"), ANUAL_2026) == _c("1739.48")

    def test_banda_1_zera_o_imposto(self):
        """Até 60.000 a norma zera; o clamp faz o resto."""
        assert redutor_devido(_c("55000"), _c("1200"), ANUAL_2026) == _c("1200")

    def test_clamp_nunca_gera_credito(self):
        """Art. 11-A: a redução é limitada ao imposto apurado."""
        assert redutor_devido(_c("62000"), _c("500"), ANUAL_2026) == _c("500")

    def test_sem_imposto_nao_ha_o_que_reduzir(self):
        assert redutor_devido(_c("70000"), 0, ANUAL_2026) == 0

    @pytest.mark.parametrize("bruto", ["59999", "60000"])
    def test_a_borda_do_piso_nao_gera_degrau_negativo(self, bruto):
        """Se a reta valesse no piso daria 2.695,23; a banda 1 dá o intercepto e o
        clamp iguala os dois — é por isso que o R$ 1,08 da norma não alcança o
        cliente (co-design 2026-08-24)."""
        assert redutor_devido(_c(bruto), _c("99999"), ANUAL_2026) == _c("8429.73")

    def test_vo_zerado_e_ano_sem_redutor(self):
        """AC <= 2025 publica o VO zerado — não `None`, e não reduz nada."""
        assert redutor_devido(_c("70000"), _c("5000"), RedutorIRPF()) == 0
