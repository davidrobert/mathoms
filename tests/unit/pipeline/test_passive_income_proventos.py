"""Tests — complemento de buckets por informes de proventos (A33.l4 · ADR-238 D4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pipeline.domain.services.fiscal_source import ProventosRendaAnual
from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    FontePagadoraPF,
)
from tests.unit.pipeline._passive_income_builders import (
    calc,
    decl,
    exclusiva,
    isento,
    patrimonio,
)

_REF_DATE = date(2025, 6, 1)
_NO_DESPESA = Decimal("0")


def _renda_proventos(ano: int = 2024, dividendos: str = "596.60", jcp: str = "272.00"):
    return (
        ProventosRendaAnual(
            ano_base=ano,
            dividendos_liquido_brl=Decimal(dividendos),
            jcp_liquido_brl=Decimal(jcp),
        ),
    )


def _calculate(d=None, *, proventos=()):
    return calc().calculate(
        irpf=IRPFAnalyzer([d]) if d is not None else None,
        patrimonio=patrimonio(),
        investimentos_atuais=None,
        reference_date=_REF_DATE,
        despesa_mensal_media_brl=_NO_DESPESA,
        proventos=proventos,
    )


class TestComplementoInformesProventos:
    def test_informe_preenche_buckets_zerados(self):
        """IRPF sem cod-09/10 + informe proventos → dividendos/jcp líquidos entram."""
        d = decl(
            exclusiva_list=[
                exclusiva(CodigoRendimentoTribExclusiva.rendimentos_aplicacoes_financeiras, "8000")
            ]
        )
        result = _calculate(d, proventos=_renda_proventos())
        fontes = result.renda_passiva_por_fonte_brl
        assert fontes["dividendos"] == Decimal("596.60")
        assert fontes["jcp"] == Decimal("272.00")
        assert result.renda_passiva_anual_brl == Decimal("8868.60")  # 8000 + 596.60 + 272

    def test_declaracao_vence_bucket_populado(self):
        """ADR-238 D4: cod-09 > 0 → informe NÃO soma (double-count); jcp zerado preenche."""
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "10000.00")])
        result = _calculate(d, proventos=_renda_proventos())
        fontes = result.renda_passiva_por_fonte_brl
        assert fontes["dividendos"] == Decimal("10000.00")  # declaração vence
        assert fontes["jcp"] == Decimal("272.00")  # bucket zerado → informe preenche

    def test_informe_de_outro_ano_nao_conta(self):
        result = _calculate(decl(ano_base=2024), proventos=_renda_proventos(ano=2023))
        assert result.renda_passiva_por_fonte_brl["dividendos"] == Decimal("0")
        assert result.renda_passiva_por_fonte_brl["jcp"] == Decimal("0")

    def test_complemento_nao_reduz_alugueis_delta(self):
        """Fill pós-delta: informes não entram em capital_total; aluguéis intactos."""
        aluguel = FontePagadoraPF(
            pagador_nome="Locatário Sintético", valor_brl="3000.00", ir_recolhido_brl="0"
        )
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "5000.00")]).model_copy(
            update={"rendimentos_pf": [aluguel]}
        )
        result = _calculate(d, proventos=_renda_proventos(dividendos="999.99", jcp="111.11"))
        fontes = result.renda_passiva_por_fonte_brl
        assert fontes["alugueis"] == Decimal("3000.00")  # delta preservado
        assert fontes["dividendos"] == Decimal("5000.00")  # declaração vence
        assert fontes["jcp"] == Decimal("111.11")  # zerado → preenche

    def test_sem_irpf_continua_sem_irpf_mesmo_com_informes(self):
        """TRS de informes-only distorceria (só div/jcp observáveis) — piso seguro."""
        result = _calculate(None, proventos=_renda_proventos())
        assert result.status == "sem_irpf"
        assert result.renda_passiva_anual_brl == Decimal("0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
