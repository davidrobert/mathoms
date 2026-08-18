"""[[ADR-392]] / [[A40.l70]] — sem canonical não minta; prova por mutação."""

from __future__ import annotations

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.domain.services.endereco_canonicalizer import canonicalize
from pipeline.domain.services.property_identity_enricher import (
    enrich_imoveis_with_property_ids,
)
from pipeline.domain.types.property_identity import PropertyLookupKey

WS = "ws-adr392"


def _imovel(descricao: str, *, year: int = 2024, codigo: str = "12") -> dict:
    return {
        "descricao": descricao,
        "proprietario": "david_robert",
        "codigo_rfb": codigo,
        "ano_referencia": year,
    }


def test_mutation_canonicalize_none_does_not_mint(monkeypatch) -> None:
    monkeypatch.setattr(
        "pipeline.domain.services.property_identity_enricher.canonicalize",
        lambda _d: None,
    )
    resolver = InMemoryPropertyIdentityResolver()
    out = enrich_imoveis_with_property_ids(
        {"imoveis_consolidados": [_imovel("Rua Exemplo, 100")]}, resolver, WS
    )
    entry = out["imoveis_consolidados"][0]
    assert canonicalize("Rua Exemplo, 100") == "exemplo 100"
    assert entry["property_id"] is None and entry["needs_review"] is True
    assert resolver.all() == []
    assert "domain.property_identity_uncanonical" in [r["code"] for r in entry["review_reasons"]]


def test_regrowth_three_spellings_never_makes_three_rows() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    for year, desc in enumerate(("APTO SEM NUMERO", "apto sem numero ", "Apto Sem Numero"), 2022):
        payload = {"imoveis_consolidados": [_imovel(desc, year=year, codigo="11")]}
        enrich_imoveis_with_property_ids(payload, resolver, WS)
    assert len(resolver.all()) <= 1


def test_inmemory_residual_unique_matches_one_row() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    seeded = resolver._insert(
        WS,
        PropertyLookupKey("david_robert", "11", None),
        2022,
    )
    got = resolver.match_or_create(
        WS, PropertyLookupKey("david_robert", "11", None), 2024, "grafia nova"
    )
    assert got is not None and got.property_id == seeded.property_id


# Regressão do #1508: `codigo_rfb` é código de CATEGORIA (11 = imóveis), então
# (titular, codigo_rfb) casa com todo imóvel da pessoa. O residual reivindicava o
# imóvel legítimo, e o item sem canonical herdava `property_id` E
# `endereco_canonical` — o dedup seguinte fundia os dois e o valor sumia.
def test_residual_nao_reivindica_row_que_tem_canonical_propria() -> None:
    resolver = InMemoryPropertyIdentityResolver()
    resolver._insert(WS, PropertyLookupKey("david_robert", "11", "exemplo 100"), 2024)
    got = resolver.match_or_create(
        WS, PropertyLookupKey("david_robert", "11", None), 2024, "FINANCIAMENTO IMOVEL EXEMPLO"
    )
    assert got is None


def test_item_sem_canonical_nao_absorve_o_valor_do_imovel_legitimo() -> None:
    """O -200k tem de sobreviver como entrada própria, não virar dedup do 600k."""
    payload = {
        "imoveis_consolidados": [
            _imovel("Rua Exemplo, 100", codigo="11") | {"valor": 600000.0},
            _imovel("FINANCIAMENTO IMOVEL EXEMPLO", codigo="11") | {"valor": -200000.0},
        ]
    }
    out = enrich_imoveis_with_property_ids(payload, InMemoryPropertyIdentityResolver(), WS)
    legitimo, financiamento = out["imoveis_consolidados"]
    assert canonicalize("FINANCIAMENTO IMOVEL EXEMPLO") is None
    assert legitimo["property_id"] is not None
    assert financiamento["property_id"] is None
    assert financiamento["endereco_canonical"] != legitimo["endereco_canonical"]
