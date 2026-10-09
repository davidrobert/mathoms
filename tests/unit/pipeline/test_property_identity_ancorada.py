"""Enricher com âncora: plano read-only, veto por unidade e mint em duas fases ([[ADR-440]] D6/D7)."""

# Rows semeadas com o `canonical` que cada era gravou; itens chegam como o E1.5c os monta
# na era da discriminação literal — descrição curta + `ancora_imovel`. Valores inventados.

from __future__ import annotations

import pytest

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.domain.services import property_identity_enricher as enricher
from pipeline.domain.types.property_identity import PropertyLookupKey

_WS = "ws-1"


def _semear(resolver, canonical: str, amostra: str, codigo: str = "11") -> str:
    lookup = PropertyLookupKey("titular", codigo, canonical)
    return resolver.match_or_create(_WS, lookup, 2023, amostra).property_id


def _item(descricao: str, codigo: str = "11", **ancora) -> dict:
    item = {
        "descricao": descricao,
        "proprietario": "titular",
        "codigo_rfb": codigo,
        "eixo_autoridade": "secao",
        "ano_referencia": 2024,
    }
    return {**item, "ancora_imovel": {"join": "valor", **ancora}} if ancora else item


def _enriquecer(resolver, *itens: dict) -> list[dict]:
    consolidado = {"imoveis_consolidados": list(itens)}
    enricher.enrich_imoveis_with_property_ids(consolidado, resolver=resolver, workspace_id=_WS)
    return consolidado["imoveis_consolidados"]


def _codes(item: dict) -> list[str]:
    return [r["code"] for r in item.get("review_reasons") or []]


# Matrícula sintética de dígitos repetidos: dois aptos precisam de duas distintas.
_AMOSTRA_11 = "APARTAMENTO 11 - Rua Exemplo, 100 - APTO 11 - MATRICULA 111111"  # noqa: PII-ok


@pytest.mark.parametrize(
    ("canonical", "ancora"),
    [
        ("exemplo 100", {"logradouro": "Rua Exemplo", "numero": "100"}),
        ("mat:999999", {"matricula": "999.999"}),
        ("iptu:12345678901", {"inscricao_municipal": "123.456.7890-1"}),
    ],
    ids=["via_numero", "mat", "iptu"],
)
def test_cada_nivel_sozinho_re_anexa_sem_cunhar(canonical, ancora) -> None:
    resolver = InMemoryPropertyIdentityResolver()
    pid = _semear(resolver, canonical, "AMOSTRA DA ERA 1.3.0")
    (item,) = _enriquecer(resolver, _item("CASA EXEMPLO", **ancora))
    assert (item["property_id"], len(resolver.all())) == (pid, 1)


def test_dois_apartamentos_do_mesmo_predio_nao_fundem() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    pid = _semear(resolver, "exemplo 100", _AMOSTRA_11)
    ancora = {"logradouro": "Rua Exemplo", "numero": "100"}
    apto11, apto22 = _enriquecer(
        resolver,
        _item("APARTAMENTO 11", matricula="111111", **ancora),
        _item("APARTAMENTO 22", matricula="222222", **ancora),
    )
    assert apto11["property_id"] == pid
    assert apto22["property_id"] not in (None, pid)
    assert apto22["endereco_canonical"] == "mat:222222"


def test_sem_o_veto_os_dois_apartamentos_fundem(monkeypatch) -> None:
    """Contrafactual: é a comparação de unidade que separa o que o via+nº juntou."""
    monkeypatch.setattr(enricher, "comparar_unidades", lambda a, b: None)
    resolver = InMemoryPropertyIdentityResolver()
    pid = _semear(resolver, "exemplo 100", _AMOSTRA_11)
    ancora = {"logradouro": "Rua Exemplo", "numero": "100"}
    apto11, apto22 = _enriquecer(
        resolver,
        _item("APARTAMENTO 11", matricula="111111", **ancora),
        _item("APARTAMENTO 22", matricula="222222", **ancora),
    )
    assert apto11["property_id"] == apto22["property_id"] == pid


def test_row_sem_unidade_disputada_por_duas_unidades_nao_anexa_nem_cunha() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    _semear(resolver, "exemplo 100", "IMOVEL - Rua Exemplo, 100")
    ancora = {"logradouro": "Rua Exemplo", "numero": "100"}
    a, b = _enriquecer(
        resolver,
        _item("UNIDADE A", matricula="111111", **ancora),
        _item("UNIDADE B", matricula="222222", **ancora),
    )
    assert a["property_id"] is None and b["property_id"] is None
    assert _codes(a) == _codes(b) == ["domain.property_identity_sem_posse"]
    assert len(resolver.all()) == 1


def test_mesmo_imovel_em_dois_anos_cai_na_mesma_row() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    pid = _semear(resolver, "exemplo 100", _AMOSTRA_11)
    ancora = {"logradouro": "Rua Exemplo", "numero": "100", "matricula": "111111"}
    ano1, ano2 = _enriquecer(resolver, _item("APTO 11", **ancora), _item("APTO 11", **ancora))
    assert ano1["property_id"] == ano2["property_id"] == pid
    assert _codes(ano1) == _codes(ano2) == []


def test_imovel_novo_em_dois_anos_cunha_uma_vez_em_via() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    ancora = {"logradouro": "Rua Exemplo", "numero": "100", "matricula": "333333"}
    ano1, ano2 = _enriquecer(resolver, _item("CASA", **ancora), _item("CASA", **ancora))
    assert ano1["property_id"] == ano2["property_id"]
    assert [r.endereco_canonical for r in resolver.all()] == ["exemplo 100"]


def test_duas_unidades_novas_no_mesmo_predio_cunham_em_matricula() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    ancora = {"logradouro": "Rua Exemplo", "numero": "100"}
    _enriquecer(
        resolver,
        _item("APTO 1", matricula="111111", **ancora),
        _item("APTO 2", matricula="222222", **ancora),
    )
    assert sorted(r.endereco_canonical for r in resolver.all()) == ["mat:111111", "mat:222222"]


def test_row_provada_por_unidade_vence_e_a_outra_vira_split() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    so_endereco = _semear(resolver, "exemplo 100", "IMOVEL - Rua Exemplo, 100")
    provada = _semear(resolver, "mat:111111", "CASA - MATRICULA 111111")  # noqa: PII-ok
    ancora = {"logradouro": "Rua Exemplo", "numero": "100", "matricula": "111111"}
    (item,) = _enriquecer(resolver, _item("CASA", **ancora))
    assert item["property_id"] == provada
    razao = item["review_reasons"][0]
    assert razao["code"] == "domain.property_identity_split"
    assert razao["offending_value"] == f"property_ids={so_endereco}"


def test_a_ancora_sai_do_item_e_o_item_sem_ancora_segue_o_caminho_de_hoje() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    legado = {k: v for k, v in _item("APARTAMENTO - Rua Exemplo, 100").items()}
    ancorado = _item("CASA", logradouro="Rua Exemplo", numero="200")
    itens = _enriquecer(resolver, legado, ancorado)
    assert all("ancora_imovel" not in i for i in itens)
    assert itens[0]["endereco_canonical"] == "exemplo 100"


def test_descartar_ancoras_e_idempotente_e_roda_sem_resolver() -> None:
    consolidado = {"imoveis_consolidados": [_item("CASA", logradouro="Rua Exemplo", numero="1")]}
    enricher.descartar_ancoras(consolidado)
    enricher.descartar_ancoras(consolidado)
    assert "ancora_imovel" not in consolidado["imoveis_consolidados"][0]
