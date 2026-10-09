"""Identidade de imóvel lê o SUB-código RFB — `'01-11'` e `'11'` são o mesmo apartamento.

O roteamento (`grupo_rfb`) lê o grupo; a identidade lê o sub-código, que é o que separa
apartamento de casa e o que o código plano das declarações anteriores já trazia. Composto
de outro grupo não tem sub-código de imóvel ([[ADR-225]] §Emenda 2026-10-08).
"""

from __future__ import annotations

import pytest

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.domain.services.baseline_item_classifier import (
    codigo_rfb_do_imovel,
    subcodigo_imovel_rfb,
)
from pipeline.domain.services.property_identity_enricher import enrich_imoveis_with_property_ids
from pipeline.domain.types.property_identity import PropertyLookupKey

_CASA = "CASA - Rua Exemplo, 100"


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        ("01-11", "11"),
        ("01-12", "12"),
        ("1-1", "01"),
        ("G01-11", "11"),
        ("11", "11"),
        (" 12 ", "12"),
        (11, "11"),
        ("1", "01"),
        ("G01", "01"),
        ("01", "01"),
    ],
)
def test_sub_codigo_das_duas_grafias(codigo, esperado):
    assert subcodigo_imovel_rfb(codigo) == esperado


# `'07-01'` daria `'01'`, o genérico que o dedup funde com qualquer específico.
@pytest.mark.parametrize(
    "codigo", ["07-01", "04-02", "", None, "APTO", "11 - APARTAMENTO", "0111", "01 - 11"]
)
def test_sem_sub_codigo_de_imovel_devolve_none(codigo):
    assert subcodigo_imovel_rfb(codigo) is None


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [("01-11", "11"), ("G01", "01"), ("07-01", "07-01"), ("APTO", "APTO"), (None, "")],
)
def test_campo_guarda_o_cru_quando_nao_ha_sub_codigo(codigo, esperado):
    """O artefato é evidência: o cru ilegível fica visível, e o enricher recusa a chave."""
    assert codigo_rfb_do_imovel(codigo) == esperado


def _item(codigo: str, descricao: str = _CASA) -> dict:
    return {
        "codigo": codigo,
        "descricao": descricao,
        "categoria_hint": "imovel",
        "secao": "bens_direitos",
        "valor_brl": "100000.00",
        "membro": "titular",
        "ano": 2025,
    }


@pytest.mark.parametrize(
    ("codigo", "esperado"), [("01-11", "11"), ("11", "11"), ("07-01", "07-01")]
)
def test_produtor_de_itens_grava_o_sub_codigo(codigo, esperado):
    from scripts.consolidate_baseline import consolidate_from_itens

    out = consolidate_from_itens({"itens": [_item(codigo)], "resumo": {"ano_referencia": 2025}})
    [imovel] = out["imoveis_consolidados"]
    assert imovel["codigo_rfb"] == esperado


def test_produtor_legado_grava_o_sub_codigo(monkeypatch):
    """`bens_direitos[].grupo` cru (`'G01'`) era o segundo produtor do campo."""
    import scripts.consolidate_baseline as cb

    monkeypatch.setattr(cb, "_MEMBER_KEYS", ["titular"])
    bem = {"grupo": "G01", "situacao_atual": 100, "descricao": _CASA}
    decl = {"membro": "titular", "ano_base": 2024, "bens_direitos": [bem], "dividas": []}
    [imovel] = cb.consolidate({"declarations": [decl]})["imoveis_consolidados"]
    assert imovel["codigo_rfb"] == "01"


def _enrich(codigo: str) -> tuple[dict, InMemoryPropertyIdentityResolver]:
    resolver = InMemoryPropertyIdentityResolver()
    imovel = {"descricao": _CASA, "proprietario": "titular", "codigo_rfb": codigo}
    enrich_imoveis_with_property_ids({"imoveis_consolidados": [imovel]}, resolver, "ws-1")
    return imovel, resolver


def test_enricher_chaveia_pelo_sub_codigo():
    imovel, resolver = _enrich("01-12")
    assert imovel["property_id"] is not None
    assert [r.codigo_rfb for r in resolver.all()] == ["12"]


def test_codigo_sem_sub_codigo_de_imovel_vai_a_revisao_com_razao_propria():
    """Não é `uncanonical`: aquele manda consertar o endereço, e o defeito é o código."""
    imovel, resolver = _enrich("07-01")
    [razao] = imovel["review_reasons"]
    assert razao["code"] == "domain.property_identity_codigo_invalido"
    assert razao["offending_value"] == "codigo_rfb='07-01'"
    assert imovel["property_id"] is None and imovel["endereco_canonical"] is None
    assert imovel["needs_review"] is True and resolver.all() == []


def test_codigo_ausente_segue_no_caminho_uncanonical():
    imovel, _ = _enrich("")
    assert [r["code"] for r in imovel["review_reasons"]] == ["domain.property_identity_uncanonical"]


def test_chave_recusa_grafia_crua():
    """Grafia crua na chave é erro de programação — em Postgres só estouraria no INSERT."""
    with pytest.raises(ValueError, match="'01-11'"):
        PropertyLookupKey(titular_key="titular", codigo_rfb="01-11", endereco_canonical=None)
    assert PropertyLookupKey("titular", "11", None).codigo_rfb == "11"
