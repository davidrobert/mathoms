"""Contrato do artefato E1.5 — a âncora `cnpj_emissor` e o produtor real ([[A42.l15]] PR0)."""

# Dois buracos distintos, e o segundo é o que valia o PR:
#
# 1. `additionalProperties: false` REJEITAVA `cnpj_emissor` (medido antes do PR0), o que
#    fazia do produtor da [[ADR-271]] §147 uma mudança impossível de mergear sozinha.
# 2. Nada aqui schema-validava a SAÍDA REAL de `_output_to_baseline_json` — o teste que
#    existia (`test_agregado_misto_valida_contra_o_schema`) valida um LITERAL. Literal e
#    produtor divergem em silêncio: o schema é `additionalProperties: false`, então basta
#    uma chave nova no produtor para o artefato passar a violar o contrato sem teste cair.

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput, PatrimonialItem
from pipeline.stages.extract_baseline import _output_to_baseline_json
from scripts.pipeline_common import _build_schema_validator, _schema_to_validate

_SCHEMA_NAME = "e15_baseline_extract.schema.json"


def _erros(payload: dict) -> list[str]:
    schema, _ = _schema_to_validate(_SCHEMA_NAME)
    assert schema is not None, f"{_SCHEMA_NAME} não resolve — o teste seria vacuamente verde"
    return [e.message for e in _build_schema_validator(schema).iter_errors(payload)]


def _item_rico() -> PatrimonialItem:
    """TODO campo opcional preenchido — item mínimo não exercita `additionalProperties`."""
    return PatrimonialItem(
        code="41",
        description="CDB BANCO EXEMPLO CNPJ 12.345.678/0001-95",
        category_hint="investimento",
        secao="bens_direitos",
        institution="Banco Exemplo",
        value_brl=Decimal("600000.00"),
        member_key="m1",
        year=2024,
        cpf="12345678901",
    )


def _saida_do_produtor() -> dict:
    output = BaselinePatrimonialOutput(
        items=[_item_rico()],
        total_assets_brl=Decimal("600000.00"),
        total_liabilities_brl=Decimal("0.00"),
        net_worth_brl=Decimal("600000.00"),
        reference_year=2024,
        confidence=0.9,
    )
    return _output_to_baseline_json(output)


def test_saida_real_do_produtor_valida_contra_o_schema() -> None:
    """O que o E1.5 grava — não um literal escrito à mão ao lado do produtor."""
    assert _erros(_saida_do_produtor()) == []


def test_chave_que_o_produtor_emite_esta_declarada_no_schema() -> None:
    """Diferença de CONJUNTO, não de contagem: o assert diz QUAL chave escapou."""
    # Pega o produtor que ganha campo sem passar pelo contrato — o modo de falha que
    # `additionalProperties: false` transforma em artefato inválido em produção.
    schema, _ = _schema_to_validate(_SCHEMA_NAME)
    declaradas = set(schema["properties"]["itens"]["items"]["properties"])
    emitidas = set(_saida_do_produtor()["itens"][0])
    escaparam = emitidas - declaradas
    assert escaparam == set(), f"produtor emite chave não declarada: {escaparam}"


def test_ancora_cnpj_e_aceita_pelo_contrato() -> None:
    """Pré-requisito DURO do produtor da [[ADR-271]] §147 — antes do PR0 isto reprovava."""
    payload = _saida_do_produtor()
    payload["itens"][0]["cnpj_emissor"] = "12345678000195"
    assert _erros(payload) == []


@pytest.mark.parametrize(
    "forma",
    ["12.345.678/0001-95", "1234567800019", "123456780001950", "", "12345678/0001-95"],
)
def test_ancora_fora_dos_14_digitos_e_recusada(forma: str) -> None:
    """O `pattern` é o sinal que pega produtor sem o normalizador determinístico."""
    # A declaração renderiza o CNPJ COM máscara; o molde que a torna emissível é
    # `informe_aluguel.imobiliaria_cnpj` ([[ADR-288]]) — `pattern` de 14 dígitos MAIS um
    # `field_validator(mode="before")` que descarta a máscara. `pattern` sem normalizador
    # é reask; normalizador sem `pattern` é máscara vazando para a raiz do CNPJ.
    payload = _saida_do_produtor()
    payload["itens"][0]["cnpj_emissor"] = forma
    assert _erros(payload) != [], f"forma {forma!r} passou — o pattern não está pegando"
