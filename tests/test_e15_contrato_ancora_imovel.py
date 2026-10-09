"""Contrato do artefato E1.5 — a âncora `ancora_imovel` da ficha de imóvel ([[A40.l121]] PR0)."""

# O PR0 só prova a FORMA: o schema aceita a âncora de [[ADR-440]] D3 e recusa o resto.
# Que a saída real do produtor valide contra ele é gate do PR do parser, porque até lá
# nenhum produtor emite a chave. Cada recusa afirma a palavra-chave EXATA do validador E o
# caminho onde ela dispara: contra o schema anterior, `bairro` reprovava por
# `additionalProperties` no ITEM (a âncora inteira era chave estranha) — mesma palavra,
# mecanismo errado, e o caso passava sem provar nada.

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput, PatrimonialItem
from pipeline.stages.extract_baseline import _output_to_baseline_json
from scripts.pipeline_common import _build_schema_validator, _schema_to_validate

_SCHEMA_NAME = "e15_baseline_extract.schema.json"


_ANCORA = ("itens", 0, "ancora_imovel")


def _palavras_que_reprovam(payload: dict) -> set[tuple[str, tuple]]:
    schema, _ = _schema_to_validate(_SCHEMA_NAME)
    assert schema is not None, f"{_SCHEMA_NAME} não resolve — o teste seria vacuamente verde"
    erros = _build_schema_validator(schema).iter_errors(payload)
    return {(e.validator, tuple(e.absolute_path)) for e in erros}


def _payload_com_imovel() -> dict:
    item = PatrimonialItem(
        code="11",
        description="APARTAMENTO ALFA",
        category_hint="imovel",
        secao="bens_direitos",
        value_brl=Decimal("100000.00"),
        member_key="m1",
        year=2024,
    )
    output = BaselinePatrimonialOutput(
        items=[item], total_assets_brl=Decimal("100000.00"), reference_year=2024, confidence=0.9
    )
    return _output_to_baseline_json(output)


def _com_ancora(ancora: object) -> dict:
    payload = _payload_com_imovel()
    payload["itens"][0]["ancora_imovel"] = ancora
    return payload


def test_substrato_sem_ancora_ja_valida() -> None:
    """Sem isto, um erro do próprio substrato faria toda recusa abaixo passar por engano."""
    assert _palavras_que_reprovam(_payload_com_imovel()) == set()


@pytest.mark.parametrize(
    "ancora",
    [
        {"join": "valor", "logradouro": "RUA ALFA", "numero": "100"},
        {"join": "valor_tokens", "matricula": "12345"},
        {
            "join": "valor",
            "logradouro": "AVENIDA BETA",
            "numero": "S/N",
            "complemento": "APTO 1 BLOCO B",
            "matricula": "12.345",
            "inscricao_municipal": "000.000.0000-0",
        },
    ],
)
def test_ancora_da_adr_440_e_aceita(ancora: dict) -> None:
    assert _palavras_que_reprovam(_com_ancora(ancora)) == set()


@pytest.mark.parametrize(
    ("ancora", "esperado"),
    [
        ({}, {("required", _ANCORA), ("minProperties", _ANCORA)}),
        ({"join": "valor"}, {("minProperties", _ANCORA)}),
        ({"logradouro": "RUA ALFA", "numero": "100"}, {("required", _ANCORA)}),
        ({"join": "llm", "numero": "100"}, {("enum", _ANCORA + ("join",))}),
        ({"join": "valor", "numero": "100", "bairro": "X"}, {("additionalProperties", _ANCORA)}),
        ({"join": "valor", "numero": "100", "cep": "00000"}, {("additionalProperties", _ANCORA)}),
        ({"join": "valor", "complemento": ""}, {("minLength", _ANCORA + ("complemento",))}),
        ({"join": "valor", "logradouro": "R" * 81}, {("maxLength", _ANCORA + ("logradouro",))}),
        ({"join": "valor", "numero": 100}, {("type", _ANCORA + ("numero",))}),
    ],
)
def test_forma_fora_da_adr_440_e_recusada_pelo_mecanismo_certo(ancora, esperado) -> None:
    """Bairro e CEP ficam fora por minimização; complemento vazio é omitido, nunca `""`."""
    assert _palavras_que_reprovam(_com_ancora(ancora)) == esperado


@pytest.mark.parametrize(
    ("versao", "esperado"),
    [
        ("1.0.0", set()),
        ("v1", {("pattern", ("ancora_versao",))}),
        (1, {("type", ("ancora_versao",))}),
    ],
)
def test_ancora_versao_na_raiz_e_semver(versao, esperado) -> None:
    payload = _payload_com_imovel()
    payload["ancora_versao"] = versao
    assert _palavras_que_reprovam(payload) == esperado
