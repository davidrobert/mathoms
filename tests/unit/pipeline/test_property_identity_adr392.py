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
