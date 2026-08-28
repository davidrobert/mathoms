"""A base da alíquota efetiva é a renda BRUTA da família, não a parcela tributável."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.domain.services.ratios_calculator import RatiosCalculator
from pipeline.llm.schemas.e16_irpf_full import ImpostoApurado, IRPFFullOutput, RendimentoIsento
from tests.unit.pipeline.test_ratios_calculator import (
    _build_contribuinte_for_aliquota,
    _build_pj_for_aliquota,
    _fluxo_with_janela,
    _patrimonio,
)


def _irpf_com_isentos(*, tributavel: str, ir_pago: str, isentos: str) -> IRPFAnalyzer:
    decl = IRPFFullOutput(
        contribuinte=_build_contribuinte_for_aliquota(2024),
        rendimentos_pj=[_build_pj_for_aliquota(tributavel, ir_pago)],
        rendimentos_isentos=[
            RendimentoIsento(codigo_rfb="09", descricao="Lucros e dividendos", valor_brl=isentos)
        ],
        imposto_apurado=ImpostoApurado(
            base_calculo_brl=tributavel,
            ir_devido_brl=ir_pago,
            deducoes_totais_brl="0",
            ir_pago_brl=ir_pago,
        ),
        confidence=0.95,
    )
    return IRPFAnalyzer([decl])


# C14 (A40.l80): o catálogo declarava `renda_tributavel` para um número que o produtor
# divide por tributável + isentos + exclusiva (`irpf_analyzer._renda_total`). Enquanto
# toda fixture montava só `rendimentos_pj`, as duas leituras COINCIDIAM e o rótulo errado
# era indistinguível do certo — a fixture, não o gate, é que era cega. Com dividendos
# isentos, o caso do ICP, elas divergem 4×: 3,75% contra 15,00% pela tributável.
def test_aliquota_efetiva_divide_pela_renda_bruta_e_declara_essa_base():
    irpf = _irpf_com_isentos(tributavel="100000.00", ir_pago="15000.00", isentos="300000.00")

    r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio(), irpf=irpf)

    assert r.aliquota_efetiva_ir_pct == Decimal("3.75")
    assert r.to_legacy_dict()["base_aliquota_efetiva_ir_pct"] == "renda_anual_familiar"
