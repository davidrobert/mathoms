"""Chave por nível e unidade a partir da âncora da ficha ([[A40.l121]] · [[ADR-440]] D5/D6)."""

# A chave montada da âncora tem de sair BYTE-IGUAL à que `canonicalize` gravou nas rows:
# se divergir, o match estrito e o loose perdem a row e o mint órfã a classificação.

from __future__ import annotations

import pytest

from pipeline.domain.services.ancora_imovel_identidade import (
    Unidade,
    chaves_da_ancora,
    comparar_unidades,
    subcodigos_divergem,
    unidade_da_ancora,
    unidade_da_row,
)
from pipeline.domain.services.endereco_canonicalizer import canonical_do_nivel, canonicalize


@pytest.mark.parametrize(
    ("descricao", "nivel"),
    [
        ("APARTAMENTO - Rua Exemplo, 100 - APTO 1", "via_numero"),
        ("CASA NO LOTE 3 - MATRICULA 999.999", "mat"),
        ("TERRENO - INSCRICAO MUNICIPAL (IPTU): 123.456.7890-1", "iptu"),
    ],
)
def test_canonical_do_nivel_e_o_formato_que_canonicalize_grava(descricao, nivel) -> None:
    assert canonical_do_nivel(descricao, nivel) == canonicalize(descricao)


def test_nivel_desconhecido_falha_alto() -> None:
    with pytest.raises(ValueError, match="nível de cascata desconhecido"):
        canonical_do_nivel("Rua Exemplo, 100", "cep")


def test_chaves_da_ancora_batem_com_as_rows_que_a_descricao_dobrada_cunhou() -> None:
    """Paridade com a era 1.3.0: a descrição dobrava os mesmos campos que a ficha traz."""
    ancora = {
        "join": "valor",
        "logradouro": "Rua Exemplo",
        "numero": "100",
        "matricula": "999.999",
        "inscricao_municipal": "123.456.7890-1",
    }
    assert chaves_da_ancora(ancora) == [
        canonicalize("Rua Exemplo, 100"),
        canonicalize("MATRICULA 999.999"),
        canonicalize("IPTU: 123.456.7890-1"),
    ]


def test_ancora_sem_campo_de_chave_nao_tem_chave() -> None:
    assert chaves_da_ancora({"join": "valor", "complemento": "APTO 1"}) == []
    assert chaves_da_ancora({"join": "valor", "logradouro": "Rua Exemplo"}) == []


def test_unidade_da_ancora_e_da_row_normalizam_igual() -> None:
    ancora = {"join": "valor", "matricula": "999.999", "complemento": "APTO 42"}
    amostra = "APARTAMENTO 42 - Rua Exemplo, 100 - APTO 42 - MATRICULA 999.999"
    assert unidade_da_ancora(ancora) == Unidade(matricula="999999", complemento="42")
    assert unidade_da_row("exemplo 100", amostra).matricula == "999999"
    assert unidade_da_row("mat:123456", "") == Unidade(matricula="123456")


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [
        (Unidade(matricula="1111"), Unidade(matricula="1111"), True),
        (Unidade(matricula="1111"), Unidade(matricula="2222"), False),
        (Unidade(matricula="1111"), Unidade(inscricao="5555"), None),
        (Unidade(matricula="1111", complemento="11"), Unidade(complemento="22"), False),
        (Unidade(), Unidade(matricula="1111"), None),
    ],
)
def test_compara_no_primeiro_nivel_com_valor_nos_dois_lados(a, b, esperado) -> None:
    assert comparar_unidades(a, b) is esperado


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [("11", "12", True), ("11", "01-11", False), ("11", "19", True), ("11", "", False)],
)
def test_subcodigo_especifico_diferente_diverge(a, b, esperado) -> None:
    assert subcodigos_divergem(a, b) is esperado
