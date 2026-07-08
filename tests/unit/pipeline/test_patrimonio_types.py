"""Testes unitários para ``pipeline.domain.services.patrimonio_types``.

Foco em:
- Value objects (MemberIdentity, PatrimonioConfig, CaixaDetalhe, PatrimonioInputs).
- Extractors triviais (imovel_valor, imovel_desc, veiculo_valor, investimento_valor, get_bens).
- safe_float utility.
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.patrimonio_types import (
    CaixaDetalhe,
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
    get_bens,
    imovel_desc,
    imovel_valor,
    investimento_valor,
    safe_float,
    veiculo_valor,
)

# =============================================================================
# safe_float
# =============================================================================


def test_safe_float_int():
    assert safe_float(42) == 42.0


def test_safe_float_float():
    assert safe_float(3.14) == 3.14


def test_safe_float_numeric_str():
    assert safe_float("1234.56") == 1234.56


def test_safe_float_none_returns_default():
    assert safe_float(None) == 0.0


def test_safe_float_none_returns_custom_default():
    assert safe_float(None, default=-1.0) == -1.0


def test_safe_float_unparseable_str_returns_default():
    assert safe_float("abc") == 0.0


def test_safe_float_empty_str_returns_default():
    assert safe_float("") == 0.0


def test_safe_float_dict_returns_default():
    assert safe_float({"not": "numeric"}) == 0.0


# =============================================================================
# MemberIdentity
# =============================================================================


def test_member_identity_is_frozen():
    m = MemberIdentity(
        titular_key="david", conjuge_key="mariana", titular_nome="David", conjuge_nome="Mariana"
    )
    with pytest.raises(Exception):
        m.titular_key = "other"  # type: ignore[misc]


def test_member_identity_key_inv_titular():
    m = MemberIdentity(
        titular_key="david", conjuge_key="mariana", titular_nome="David", conjuge_nome="Mariana"
    )
    assert m.key_inv_titular == "investimentos_david"


def test_member_identity_key_inv_conjuge():
    m = MemberIdentity(
        titular_key="david", conjuge_key="mariana", titular_nome="David", conjuge_nome="Mariana"
    )
    assert m.key_inv_conjuge == "investimentos_mariana"


def test_member_identity_empty_conjuge_key():
    """Fluxo de titular solo (sem cônjuge)."""
    m = MemberIdentity(titular_key="joao", conjuge_key="", titular_nome="João", conjuge_nome="")
    assert m.key_inv_conjuge == "investimentos_"


# =============================================================================
# PatrimonioConfig
# =============================================================================


def test_patrimonio_config_holds_identity_and_overrides():
    m = MemberIdentity(titular_key="d", conjuge_key="m", titular_nome="D", conjuge_nome="M")
    cfg = PatrimonioConfig(
        members=m, property_classification_overrides={"prop-1": "residencia_principal"}
    )
    assert cfg.members == m
    assert cfg.property_classification_overrides == {"prop-1": "residencia_principal"}


def test_patrimonio_config_is_frozen():
    m = MemberIdentity(titular_key="d", conjuge_key="m", titular_nome="D", conjuge_nome="M")
    cfg = PatrimonioConfig(members=m)
    with pytest.raises(Exception):
        cfg.property_classification_overrides = {"prop-z": "locado"}  # type: ignore[misc]


# =============================================================================
# CaixaDetalhe
# =============================================================================


def test_caixa_detalhe_to_dict_rounds_to_2():
    d = CaixaDetalhe(
        conta="bofa_usd",
        moeda="USD",
        saldo_original=123.4567,
        valor_brl=719.9999,
        tipo="moeda_estrangeira",
    )
    assert d.to_dict() == {
        "conta": "bofa_usd",
        "moeda": "USD",
        "saldo_original": 123.46,
        "valor_brl": 720.0,
        "tipo": "moeda_estrangeira",
        "fonte": "extrato",
    }


# =============================================================================
# PatrimonioInputs
# =============================================================================


def test_inputs_has_current_positions_false_when_none():
    inp = PatrimonioInputs(baseline={}, investimentos_atuais=None)
    assert inp.has_current_positions is False


def test_inputs_has_current_positions_false_when_empty_dados():
    inp = PatrimonioInputs(baseline={}, investimentos_atuais={"dados": []})
    assert inp.has_current_positions is False


def test_inputs_has_current_positions_false_when_not_dict():
    inp = PatrimonioInputs(baseline={}, investimentos_atuais="not a dict")  # type: ignore[arg-type]
    assert inp.has_current_positions is False


def test_inputs_has_current_positions_true_when_dados_nonempty():
    inp = PatrimonioInputs(
        baseline={},
        investimentos_atuais={"dados": [{"valor": 1000}]},
    )
    assert inp.has_current_positions is True


def test_inputs_default_caixa_empty():
    inp = PatrimonioInputs(baseline={})
    assert inp.caixa_total_brl == 0.0
    assert inp.caixa_detalhes == []


# =============================================================================
# imovel_valor
# =============================================================================


def test_imovel_valor_uses_valor_31_12():
    assert imovel_valor({"valor_31_12_ano_base": 1000.50}) == 1000.50


def test_imovel_valor_fallback_valor_irpf():
    assert imovel_valor({"valor_irpf": 500.25}) == 500.25


def test_imovel_valor_fallback_valor():
    assert imovel_valor({"valor": 300.75}) == 300.75


def test_imovel_valor_priority_31_12_over_irpf():
    assert imovel_valor({"valor_31_12_ano_base": 999, "valor_irpf": 777}) == 999.0


def test_imovel_valor_priority_irpf_over_valor():
    assert imovel_valor({"valor_irpf": 777, "valor": 100}) == 777.0


def test_imovel_valor_returns_zero_when_all_missing():
    assert imovel_valor({"descricao": "Só descrição"}) == 0.0


def test_imovel_valor_treats_zero_as_valid():
    """Valor zero é válido (diferente de ausente)."""
    assert imovel_valor({"valor_31_12_ano_base": 0}) == 0.0


# =============================================================================
# imovel_desc
# =============================================================================


def test_imovel_desc_prefers_description_lowercase():
    assert imovel_desc({"description": "APT DOWNTOWN"}) == "apt downtown"


def test_imovel_desc_fallback_descricao():
    assert imovel_desc({"descricao": "Casa Praia"}) == "casa praia"


def test_imovel_desc_fallback_endereco():
    assert imovel_desc({"endereco": "Rua X, 123"}) == "rua x, 123"


def test_imovel_desc_fallback_dados_completos_imovel():
    assert imovel_desc({"dados_completos": {"imovel": "SALA COMERCIAL"}}) == "sala comercial"


def test_imovel_desc_empty_when_nothing_present():
    assert imovel_desc({}) == ""


def test_imovel_desc_ignores_non_dict_dados_completos():
    """``dados_completos`` como string não deve quebrar — cai no fallback."""
    assert imovel_desc({"dados_completos": "not a dict"}) == ""


# =============================================================================
# veiculo_valor
# =============================================================================


def test_veiculo_valor_uses_valor_31_12():
    assert veiculo_valor({"valor_31_12_ano_base": 50000}) == 50000.0


def test_veiculo_valor_fallback_chain():
    assert veiculo_valor({"valor_irpf": 45000}) == 45000.0
    assert veiculo_valor({"valor": 40000}) == 40000.0


def test_veiculo_valor_zero_when_missing():
    assert veiculo_valor({"descricao": "Fusca 1970"}) == 0.0


# =============================================================================
# investimento_valor
# =============================================================================


def test_investimento_valor_dict_valor_31_12():
    assert investimento_valor({"valor_31_12_ano_base": 10000}) == 10000.0


def test_investimento_valor_dict_valor():
    assert investimento_valor({"valor": 5000}) == 5000.0


def test_investimento_valor_scalar_float():
    """v1.5 consolidated usa escalar em ``contas_bancarias``."""
    assert investimento_valor(2500.0) == 2500.0


def test_investimento_valor_scalar_str():
    assert investimento_valor("1500.50") == 1500.50


def test_investimento_valor_dict_without_value_keys_returns_zero():
    """Dict sem chaves de valor → safe_float({}) → 0.0."""
    assert investimento_valor({"tipo": "CDB"}) == 0.0


# =============================================================================
# get_bens
# =============================================================================


def test_get_bens_nested_layout():
    member = {
        "total_bens": 1000,
        "bens": {"imoveis": [{"valor": 500}], "veiculos": []},
    }
    bens = get_bens(member)
    assert bens == {"imoveis": [{"valor": 500}], "veiculos": []}


def test_get_bens_flat_layout_returns_member():
    member = {"imoveis": [{"valor": 500}], "veiculos": []}
    bens = get_bens(member)
    assert bens is member


def test_get_bens_bens_not_dict_falls_back_to_flat():
    """Se ``bens`` existir mas não for dict, retorna o próprio membro."""
    member = {"bens": "not a dict", "imoveis": []}
    assert get_bens(member) is member


def test_get_bens_empty_member():
    assert get_bens({}) == {}
