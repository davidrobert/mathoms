"""Contrato E1.5a pós-[[ADR-394]] D1/D7: `secao` é autoridade, `categoria` é hint.

Aditivo por decisão: nada vira `required` aqui. O teste que mais importa é o
`..._agregado_misto_...` — é o cenário que o modo incremental produz no primeiro
run pós-rename, com 766 artefatos históricos ainda gravados com `categoria`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput, PatrimonialItem
from pipeline.llm.validators import validate_e15_output
from pipeline.stages.extract_baseline import _output_to_baseline_json
from scripts.consolidate_baseline import consolidate_from_itens

_ITEM_NOVO = {
    "codigo": "11",
    "descricao": "novo",
    "categoria_hint": "imovel",
    "secao": "bens_direitos",
    "valor_brl": "1.00",
    "membro": "m1",
    "ano": 2024,
}
_ITEM_HISTORICO = {
    "codigo": "11",
    "descricao": "historico",
    "categoria": "imovel",
    "valor_brl": "1.00",
    "membro": "m1",
    "ano": 2023,
}
_MISTO = {
    "payload_version": 2,
    "itens": [_ITEM_NOVO, _ITEM_HISTORICO],
    "resumo": {
        "total_ativos": "2.00",
        "total_passivos": "0.00",
        "patrimonio_liquido": "2.00",
        "ano_referencia": 2024,
    },
}


def _item(**over) -> PatrimonialItem:
    base = dict(
        code="11",
        description="Rua Exemplo, 100",
        category_hint="imovel",
        value_brl=Decimal("600000.00"),
        member_key="m1",
        year=2024,
    )
    return PatrimonialItem(**{**base, **over})


def _output(items, **over) -> BaselinePatrimonialOutput:
    base = dict(
        items=items,
        total_assets_brl=Decimal("600000.00"),
        total_liabilities_brl=Decimal("0.00"),
        net_worth_brl=Decimal("600000.00"),
        reference_year=2024,
        confidence=0.9,
    )
    return BaselinePatrimonialOutput(**{**base, **over})


def _baseline_com(chave: str) -> dict:
    """Payload E1.5a mínimo cujo hint mora em `chave` (nome novo ou legado)."""
    item = {
        "codigo": "11",
        "descricao": "APT",
        chave: "imovel",
        "valor_brl": 600000.0,
        "membro": "m1",
        "ano": 2024,
    }
    return {
        "itens": [item],
        "resumo": {
            "total_ativos": 600000.0,
            "total_passivos": 0.0,
            "patrimonio_liquido": 600000.0,
            "ano_referencia": 2024,
        },
    }


def _codes(result) -> set[str]:
    return {i.code for i in result.issues}


def test_secao_ausente_nao_inventa_campo_no_artefato() -> None:
    """`secao` é OPCIONAL na etapa 1 — sem ela o artefato não ganha a chave."""
    payload = _output_to_baseline_json(_output([_item()]))
    assert "secao" not in payload["itens"][0]


def test_secao_presente_chega_ao_artefato() -> None:
    payload = _output_to_baseline_json(_output([_item(secao="dividas_onus")]))
    assert payload["itens"][0]["secao"] == "dividas_onus"


def test_produtor_emite_hint_e_nunca_o_nome_antigo() -> None:
    payload = _output_to_baseline_json(_output([_item()]))
    assert payload["itens"][0]["categoria_hint"] == "imovel"
    assert "categoria" not in payload["itens"][0]


def test_resposta_de_prompt_anterior_ainda_parseia() -> None:
    """Alias de validação: `category` do prompt 1.2.0 não pode brickar a extração."""
    item = PatrimonialItem(
        code="11",
        description="APT",
        category="imovel",
        value_brl=Decimal("1.00"),
        member_key="m1",
        year=2024,
    )
    assert item.category_hint == "imovel"


def test_secao_fora_do_vocabulario_avisa_sem_derrubar_o_documento() -> None:
    """Boundary tolerante ([[ADR-292]]): o item vira `needs_review`, o resto extrai."""
    out = _output([_item(secao="bens_e_direitos"), _item(description="OUTRO")])
    result = validate_e15_output(out)
    assert "e15.item.unknown_secao" in _codes(result)
    assert len(_output_to_baseline_json(out)["itens"]) == 2


def test_conservacao_do_eixo_de_passivo_dispara_com_tolerancia_zero() -> None:
    """O eixo do passivo não tinha conservação nenhuma antes da [[ADR-394]] D5."""
    divida = _item(description="DIVIDA X", value_brl=Decimal("-200000.00"), secao="dividas_onus")
    fecha = _output([_item(), divida], total_liabilities_brl=Decimal("200000.00"))
    assert "e15.totals.liabilities_mismatch" not in _codes(validate_e15_output(fecha))

    # 1 centavo de diferença já é divergência — não há tolerância neste eixo.
    nao_fecha = _output([_item(), divida], total_liabilities_brl=Decimal("199999.99"))
    assert "e15.totals.liabilities_mismatch" in _codes(validate_e15_output(nao_fecha))


@pytest.mark.parametrize("chave", ["categoria_hint", "categoria"])
def test_e15c_le_os_dois_nomes(chave: str) -> None:
    """O leitor prefere o nome novo e aceita o legado — 766 artefatos o carregam."""
    out = consolidate_from_itens(_baseline_com(chave))
    assert len(out["imoveis_consolidados"]) == 1, f"{chave!r} não roteou para imóvel"


def test_agregado_misto_valida_contra_o_schema() -> None:
    """O primeiro run incremental pós-rename mistura as duas formas num `itens[]`."""
    from scripts.pipeline_common import _build_schema_validator, _schema_to_validate

    schema, _ = _schema_to_validate("e15_baseline_extract.schema.json")
    assert schema is not None
    erros = [e.message for e in _build_schema_validator(schema).iter_errors(_MISTO)]
    assert erros == [], erros
