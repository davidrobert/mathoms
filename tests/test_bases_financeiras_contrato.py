"""A40.l80 PR1 ([[ADR-412]]): contrato das bases canônicas e do `PapelMembro`.

PR de schema permissivo: nenhum produtor escreve os campos novos ainda. O que
estes testes fecham é a **classe** — schema e enum não podem divergir, e as
chaves novas têm de ser aceitas quando presentes e dispensáveis quando ausentes,
senão o PR2 (que liga o produtor) descobre o desalinhamento em produção.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pipeline.domain.services.bases_financeiras import (
    BaseFinanceira,
    PapelMembro,
    chave_de_componente,
    publicavel_sozinha,
    termos_da_base,
)
from pipeline.domain.services.patrimonio_types import MemberIdentity
from scripts.pipeline_common import validate_dict
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "schemas" / "e5_analysis.schema.json"
)


@pytest.fixture(autouse=True)
def _strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin de modo: sob `warn`, `validate_dict` devolve True incondicionalmente."""
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def _payload(**patrimonio_extra) -> dict:
    return {
        "score": {"valor": 5.0, "classificacao": "Regular"},
        "fluxo_caixa": deepcopy(FLUXO_CAIXA_MINIMO),
        "patrimonio": {"bruto": 100.0, "liquido": 80.0, **patrimonio_extra},
    }


# -- schema <-> enum: a classe, não a instância -------------------------------


def test_chaves_de_bases_no_schema_sao_exatamente_o_enum(schema: dict):
    """Base nova exige tocar schema E enum juntos — divergir é o defeito."""
    no_schema = set(schema["properties"]["patrimonio"]["properties"]["bases"]["properties"])
    assert no_schema == {b.value for b in BaseFinanceira}


def test_toda_base_declara_seus_termos():
    """Enum sem termos publicaria base cujo conteúdo só o código-fonte sabe."""
    for base in BaseFinanceira:
        assert termos_da_base(base), f"{base.value} sem termos"


def test_base_amputada_e_a_cheia_diferem_exatamente_pela_fatia_sem_dono():
    """A relação sobre a qual a [[ADR-412]] inteira se apoia, como dado."""
    cheia = set(termos_da_base(BaseFinanceira.carteira_financeira_familia))
    amputada = set(termos_da_base(BaseFinanceira.carteira_com_titular_identificado))
    assert cheia - amputada == {"investimentos_nao_atribuidos"}


def test_so_a_base_amputada_e_proibida_sozinha():
    proibidas = {b for b in BaseFinanceira if not publicavel_sozinha(b)}
    assert proibidas == {BaseFinanceira.carteira_com_titular_identificado}


# -- PapelMembro: compatível em VALOR com o que `role_of` devolve hoje --------


def test_tripwire_role_of_ainda_e_binaria_ate_o_pr2():
    """TRIPWIRE: fica vermelho no PR2; a ação lá é DELETAR, nunca relaxar."""
    identity = MemberIdentity("david", "mariana", "David", "Mariana")
    devolvidos = {
        identity.role_of("david"),
        identity.role_of("mariana"),
        identity.role_of("ninguem"),
    }
    assert devolvidos == {"titular", "conjuge"}
    assert PapelMembro.sem_dono.value not in devolvidos
    assert len(PapelMembro) == 3


def test_papel_membro_preserva_os_valores_de_hoje():
    """Migrar o call-site no PR2 não pode mover string publicada."""
    identity = MemberIdentity("david", "mariana", "David", "Mariana")
    assert PapelMembro.titular.value == identity.role_of("david")
    assert PapelMembro.conjuge.value == identity.role_of("mariana")


# -- número-neutralidade: ausente valida, presente valida, lixo NÃO valida ----


# NÃO é o gate de neutralidade: 3 chaves contra um schema de ~3.700 linhas.
# Quem mede neutralidade é `tests/test_e5_golden_execution.py`, que roda o stage.
def test_payload_sem_os_campos_novos_continua_valido():
    """Payload sem os campos novos segue válido (o gate de neutralidade é o golden)."""
    assert validate_dict(_payload(), "e5_analysis.schema.json") is True


def test_payload_com_os_campos_novos_e_aceito():
    """Sem isto o PR2 escreveria campo que o schema rejeita."""
    payload = _payload(
        bases={
            "carteira_financeira_familia": {
                "termos": list(termos_da_base(BaseFinanceira.carteira_financeira_familia)),
                "valor_brl": 100.0,
            }
        },
        atribuicao_investimentos={
            "status": "parcial",
            "pct_carteira_financeira": 48.13,
            "piso_pct": 1.0,
            "motivo": "fatia sem titular acima do piso",
        },
    )
    assert validate_dict(payload, "e5_analysis.schema.json") is True


def test_base_fora_do_enum_e_rejeitada():
    """Mutação plausível: se isto passar, `additionalProperties` foi afrouxado."""
    payload = _payload(bases={"carteira_inventada": {"valor_brl": 1.0}})
    assert validate_dict(payload, "e5_analysis.schema.json") is False


def test_status_de_atribuicao_fora_do_vocabulario_e_rejeitado():
    """O status reusa o vocabulário fechado da [[ADR-403]]; valor novo é erro."""
    payload = _payload(atribuicao_investimentos={"status": "nao_apurado"})
    assert validate_dict(payload, "e5_analysis.schema.json") is False


# Inspecionar `schema[...]["properties"]` passava verde com `type` que o produtor
# não consegue escrever; por isso aqui valida payload de verdade.
def test_composicao_liquida_aceita_o_balde_sem_dono_e_recusa_sinonimo():
    """[[ADR-412]] §D4: mesmo nome do patrimônio, sem sinônimo — validando de verdade."""
    reserva = {"composicao_liquida": {"investimentos_nao_atribuidos": 10.0}}
    ok = _payload()
    ok["reserva_emergencia"] = reserva
    assert validate_dict(ok, "e5_analysis.schema.json") is True

    tipo_errado = _payload()
    tipo_errado["reserva_emergencia"] = {
        "composicao_liquida": {"investimentos_nao_atribuidos": "10"}
    }
    assert validate_dict(tipo_errado, "e5_analysis.schema.json") is False

    sinonimo = _payload()
    sinonimo["reserva_emergencia"] = {"composicao_liquida": {"investimentos_sem_dono": 10.0}}
    assert validate_dict(sinonimo, "e5_analysis.schema.json") is False


def test_chave_de_componente_casa_o_schema(schema: dict):
    """O par papel->chave é o que impede o PR2 de montar a chave por f-string."""
    props = schema["$defs"]["ReservaComposicaoLiquida"]["properties"]
    for papel in PapelMembro:
        assert chave_de_componente(papel.value) in props
