"""Gates de publicação única do limite PGBL na cascata fiscal."""

from pipeline.domain.models.transaction import Money
from pipeline.domain.services.tributario.cascata_calculator import (
    CascataInput,
    compute,
)


def _input(anexo: str, pro_labore_mensal: str) -> CascataInput:
    return CascataInput(
        regime="simples",
        anexo_simples=anexo,
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl(pro_labore_mensal),
        folha_pj_mensal=Money.brl("0"),
        renda_tributavel_pf_irpf_anual=Money.brl("0"),
    )


def test_t3_nao_publica_segundo_limite_pgbl():
    output = compute(_input("III", "12000"))
    trigger = next(item for item in output.triggers if item.code == "T3")
    assert "pgbl_limite_anual_brl" not in trigger.params


def test_t1_suprime_aporte_e_economia_ate_diferencial_estar_disponivel():
    output = compute(_input("V", "5000"))
    trigger = next(item for item in output.triggers if item.code == "T1")
    assert "aporte_pgbl_extra_anual_brl" not in trigger.params
    assert "economia_ir_anual_brl" not in trigger.params
