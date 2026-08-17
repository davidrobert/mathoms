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
        # A40.l36: o campo é o TOTAL do IRPF. Fixture com 0 deixaria o caminho
        # PGBL/T1/T3 verde sem exercitar a regra; e 174k faria a razão de
        # elegibilidade do T1 passar de 0,80 (alvo = teto INSS 8.157,41), o que
        # DESLIGA o trigger que este teste existe para exercitar.
        # 96k = 60k declarados pela própria PJ + 36k de aluguel → razão 0,717.
        renda_tributavel_pf_irpf_anual=Money.brl("96000"),
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
