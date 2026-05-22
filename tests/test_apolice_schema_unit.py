"""A18 L2 P1 (ADR-239 D2) — schema ApolicePayload + Discriminated Union 2 níveis."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.schemas.apolice import (
    PROMPT_VERSION,
    ApolicePayload,
    BemSeguradoImovel,
    BemSeguradoVeiculo,
    CoberturaMaterial,
    CoberturaRcfv,
)

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_golden"

FIXTURE_NAMES = ("apolice_auto_simples", "apolice_residencial_simples", "apolice_combinada")


@pytest.fixture
def fixtures():
    return {name: json.loads((GOLDEN_DIR / f"{name}.json").read_text()) for name in FIXTURE_NAMES}


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_golden_parses(fixtures, name):
    ApolicePayload.model_validate(fixtures[name])  # no raise


def test_auto_simples_tem_um_veiculo(fixtures):
    p = ApolicePayload.model_validate(fixtures["apolice_auto_simples"])
    assert len(p.bens_segurados) == 1
    bem = p.bens_segurados[0]
    assert isinstance(bem, BemSeguradoVeiculo)
    assert bem.placa == "ABC1D23"
    assert bem.fipe_code == "827125-9"


def test_residencial_simples_tem_um_imovel(fixtures):
    p = ApolicePayload.model_validate(fixtures["apolice_residencial_simples"])
    assert len(p.bens_segurados) == 1
    bem = p.bens_segurados[0]
    assert isinstance(bem, BemSeguradoImovel)
    assert bem.tipo_imovel == "apartamento"
    assert bem.endereco.uf == "SP"


def test_combinada_tem_dois_bens(fixtures):
    """Critério de aceite: apólice combinada Porto renderiza len(bens_segurados)==2."""
    p = ApolicePayload.model_validate(fixtures["apolice_combinada"])
    assert len(p.bens_segurados) == 2
    tipos = sorted(bem.tipo for bem in p.bens_segurados)
    assert tipos == ["imovel", "veiculo"]


def test_combinada_dispara_cascade(fixtures):
    """cascade_triggered=True quando multi-bem."""
    p = ApolicePayload.model_validate(fixtures["apolice_combinada"])
    assert p.cascade_triggered is True


def test_lmi_modo_discriminator_valor_fixo(fixtures):
    """lmi_modo=valor_fixo → lmi_brl preenchido; lmi_fipe_percentual=null."""
    p = ApolicePayload.model_validate(fixtures["apolice_residencial_simples"])
    cov0 = p.bens_segurados[0].coberturas[0]
    assert isinstance(cov0, CoberturaMaterial)
    assert cov0.lmi_modo == "valor_fixo"
    assert cov0.lmi_brl == Decimal("400000.00")
    assert cov0.lmi_fipe_percentual is None


def test_lmi_modo_discriminator_fipe_percentual(fixtures):
    """lmi_modo=fipe_percentual → lmi_fipe_percentual preenchido; lmi_brl=null."""
    p = ApolicePayload.model_validate(fixtures["apolice_auto_simples"])
    cov0 = p.bens_segurados[0].coberturas[0]
    assert isinstance(cov0, CoberturaMaterial)
    assert cov0.lmi_modo == "fipe_percentual"
    assert cov0.lmi_fipe_percentual == Decimal("1.00")
    assert cov0.lmi_brl is None


def test_lmi_modo_primeiro_risco_absoluto(fixtures):
    """3º modo: limite fixo absoluto (independente de FIPE/valor de bem)."""
    p = ApolicePayload.model_validate(fixtures["apolice_residencial_simples"])
    cov_roubo = p.bens_segurados[0].coberturas[2]
    assert isinstance(cov_roubo, CoberturaMaterial)
    assert cov_roubo.lmi_modo == "primeiro_risco_absoluto"
    assert cov_roubo.lmi_brl == Decimal("20000.00")


def test_rcfv_cobertura_discriminator(fixtures):
    """CoberturaRcfv discriminada — danos_materiais / danos_corporais / danos_morais."""
    p = ApolicePayload.model_validate(fixtures["apolice_auto_simples"])
    rcfv_covs = [c for c in p.bens_segurados[0].coberturas if isinstance(c, CoberturaRcfv)]
    assert len(rcfv_covs) == 2
    nomes = sorted(c.nome for c in rcfv_covs)
    assert nomes == ["danos_corporais", "danos_materiais"]


def test_congenere_anterior_preserva_lineage(fixtures):
    p = ApolicePayload.model_validate(fixtures["apolice_auto_simples"])
    assert p.congenere_anterior is not None
    assert p.congenere_anterior.seguradora == "porto"
    assert p.classe_bonus == 2


def test_corretor_pj_vs_pf_discriminator(fixtures):
    """PJ (CNPJ 14 dígitos) vs PF (CPF 11 dígitos + SUSEP individual)."""
    pj = ApolicePayload.model_validate(fixtures["apolice_auto_simples"])
    assert pj.corretor.cnpj_or_cpf_kind == "cnpj"
    assert len(pj.corretor.cpf_or_cnpj) == 14

    pf = ApolicePayload.model_validate(fixtures["apolice_combinada"])
    assert pf.corretor.cnpj_or_cpf_kind == "cpf"
    assert len(pf.corretor.cpf_or_cnpj) == 11


def test_placa_normalizada_mode_before():
    """Pydantic V2 field_validator(mode='before') normaliza placa (upper, sem hífen/espaço)."""
    bem = BemSeguradoVeiculo.model_validate(
        {
            "tipo": "veiculo",
            "placa": "abc-1d23",
            "marca": "YA",
            "modelo": "NMAX",
            "ano_modelo": 2024,
        }
    )
    assert bem.placa == "ABC1D23"


def test_corretor_cnpj_normalizado_strip_punctuation():
    """CorretorRef normaliza ponto/hífen/barra antes do pattern."""
    from pipeline.llm.schemas.apolice import CorretorRef

    c = CorretorRef.model_validate(
        {
            "susep_code": "202020138",
            "nome": "Corretora Teste",
            "cpf_or_cnpj": "12.345.678/0001-99",
            "cnpj_or_cpf_kind": "cnpj",
        }
    )
    assert c.cpf_or_cnpj == "12345678000199"


def test_cpf_sempre_null_no_payload_llm(fixtures):
    """LGPD ADR-231 D8: LLM nunca retorna CPF (sempre null no payload)."""
    for name in FIXTURE_NAMES:
        p = ApolicePayload.model_validate(fixtures[name])
        assert p.pagador_cpf_masked is None, f"{name} viola LGPD: pagador_cpf"
        assert p.segurado_cpf_masked is None, f"{name} viola LGPD: segurado_cpf"


def test_sinistro_indenizacao_sempre_null_v1(fixtures):
    """Placeholder V1: sinistro_indenizacao_recebida_brl=null (evita migration breaking ADR-238)."""
    for name in FIXTURE_NAMES:
        p = ApolicePayload.model_validate(fixtures[name])
        assert p.sinistro_indenizacao_recebida_brl is None, f"{name}: campo deve ser null em V1"


def test_veiculo_id_sempre_null_no_payload_llm(fixtures):
    """FK opcional resolvida via reconciliação assíncrona (D3) — null no payload LLM."""
    auto = ApolicePayload.model_validate(fixtures["apolice_auto_simples"])
    assert auto.bens_segurados[0].veiculo_id is None


def test_imovel_id_sempre_null_no_payload_llm(fixtures):
    """FK opcional resolvida via reconciliação assíncrona contra real_estate_assets (ADR-216)."""
    res = ApolicePayload.model_validate(fixtures["apolice_residencial_simples"])
    assert res.bens_segurados[0].imovel_id is None


def test_prompt_version_bumped(fixtures):
    for name in FIXTURE_NAMES:
        assert fixtures[name]["prompt_version"] == PROMPT_VERSION


def test_top_level_lenient_aceita_campo_desconhecido():
    """ADR-238 D2: top-level extra='allow' aceita campos não previstos sem fail."""
    payload = json.loads((GOLDEN_DIR / "apolice_auto_simples.json").read_text())
    payload["_extra_diagnostic"] = {"trace_id": "abc-123"}
    p = ApolicePayload.model_validate(payload)
    assert p.apolice_numero == "AUTO-TM-20260301-A1"


def test_bem_segurado_strict_rejeita_campo_desconhecido():
    """Sub-models são strict — extra='forbid' rejeita campo não previsto."""
    with pytest.raises(ValidationError):
        BemSeguradoVeiculo.model_validate(
            {
                "tipo": "veiculo",
                "placa": "ABC1D23",
                "marca": "YA",
                "modelo": "NMAX",
                "ano_modelo": 2024,
                "extra_field_not_in_schema": "bug",
            }
        )


def test_vigencia_fim_aceita_apos_inicio():
    """Sanity: payload válido com vigencia_fim > vigencia_inicio."""
    payload = json.loads((GOLDEN_DIR / "apolice_auto_simples.json").read_text())
    p = ApolicePayload.model_validate(payload)
    assert p.vigencia_fim > p.vigencia_inicio


def test_cobertura_discriminator_rejeita_tipo_invalido():
    with pytest.raises(ValidationError):
        BemSeguradoVeiculo.model_validate(
            {
                "tipo": "veiculo",
                "placa": "ABC1D23",
                "marca": "YA",
                "modelo": "NMAX",
                "ano_modelo": 2024,
                "coberturas": [{"tipo": "tipo_inexistente", "premio_brl": "10.00"}],
            }
        )
