"""Unit tests do `lastro_resolver` (ADR-224 §5; priority override > ticker > cnpj > keyword > fallback)."""

from __future__ import annotations

import pytest

from backend.app.services.lastro_resolver import (
    AssetQuery,
    CatalogEntry,
    OverrideEntry,
    resolve_lastro_moeda,
)


def _entry(*, ticker=None, cnpj=None, match_keyword=None, lastro="USD") -> CatalogEntry:
    return CatalogEntry(
        ticker=ticker,
        cnpj=cnpj,
        match_keyword=match_keyword,
        asset_class="Internacional",
        lastro_moeda=lastro,
    )


@pytest.fixture
def catalog() -> list[CatalogEntry]:
    return [
        _entry(ticker="IVVB11"),
        _entry(cnpj="12345678000190"),
        _entry(match_keyword="btg pactual global"),
    ]


class TestResolveLastroMoeda:
    def test_ticker_hit_returns_catalog_lastro(self, catalog):
        query = AssetQuery(ticker="IVVB11", asset_class_fallback="Internacional")
        assert resolve_lastro_moeda(query, catalog=catalog, overrides=[]) == "USD"

    def test_cnpj_hit_returns_catalog_lastro(self, catalog):
        query = AssetQuery(cnpj="12345678000190", asset_class_fallback="Fundos")
        assert resolve_lastro_moeda(query, catalog=catalog, overrides=[]) == "USD"

    def test_keyword_hit_in_descricao(self, catalog):
        query = AssetQuery(
            descricao="BTG PACTUAL GLOBAL EQUITY FIM CP",
            asset_class_fallback="Fundos",
        )
        assert resolve_lastro_moeda(query, catalog=catalog, overrides=[]) == "USD"

    def test_override_wins_over_catalog(self, catalog):
        query = AssetQuery(ticker="IVVB11", asset_class_fallback="Internacional")
        overrides = [
            OverrideEntry(match_kind="ticker", asset_match_key="IVVB11", lastro_moeda="BRL")
        ]
        # User declared BRL — sobrescreve catalog USD
        assert resolve_lastro_moeda(query, catalog=catalog, overrides=overrides) == "BRL"

    def test_override_description_wins_over_keyword(self, catalog):
        query = AssetQuery(
            descricao="BTG PACTUAL GLOBAL EQUITY FIM CP",
            asset_class_fallback="Fundos",
        )
        overrides = [
            OverrideEntry(
                match_kind="description", asset_match_key="btg pactual global", lastro_moeda="MIXED"
            )
        ]
        assert resolve_lastro_moeda(query, catalog=catalog, overrides=overrides) == "MIXED"

    def test_fallback_internacional_to_usd(self):
        query = AssetQuery(descricao="Fundo desconhecido", asset_class_fallback="Internacional")
        assert resolve_lastro_moeda(query, catalog=[], overrides=[]) == "USD"

    def test_fallback_cripto_to_usd(self):
        query = AssetQuery(asset_class_fallback="Cripto")
        assert resolve_lastro_moeda(query, catalog=[], overrides=[]) == "USD"

    def test_fallback_default_to_brl(self):
        query = AssetQuery(descricao="LCA Banco X", asset_class_fallback="Renda Fixa")
        assert resolve_lastro_moeda(query, catalog=[], overrides=[]) == "BRL"

    def test_fallback_unknown_class_to_brl(self):
        query = AssetQuery(descricao="Sei lá", asset_class_fallback="Misterio")
        assert resolve_lastro_moeda(query, catalog=[], overrides=[]) == "BRL"

    def test_ticker_case_insensitive(self, catalog):
        query = AssetQuery(ticker="ivvb11", asset_class_fallback="Internacional")
        assert resolve_lastro_moeda(query, catalog=catalog, overrides=[]) == "USD"

    def test_descricao_substring_match(self, catalog):
        # match_keyword "btg pactual global" deve achar dentro da descrição completa
        query = AssetQuery(
            descricao="BTG Pactual Global Equity Investment Fund",
            asset_class_fallback="Fundos",
        )
        assert resolve_lastro_moeda(query, catalog=catalog, overrides=[]) == "USD"

    def test_empty_query_falls_back_by_class(self, catalog):
        query = AssetQuery(asset_class_fallback="Ações BR")
        assert resolve_lastro_moeda(query, catalog=catalog, overrides=[]) == "BRL"

    def test_priority_ticker_over_cnpj(self):
        cat = [_entry(ticker="IVVB11", lastro="USD"), _entry(cnpj="12345678000190", lastro="EUR")]
        # ticker hit vence cnpj hit (priority order)
        query = AssetQuery(
            ticker="IVVB11", cnpj="12345678000190", asset_class_fallback="Internacional"
        )
        assert resolve_lastro_moeda(query, catalog=cat, overrides=[]) == "USD"
