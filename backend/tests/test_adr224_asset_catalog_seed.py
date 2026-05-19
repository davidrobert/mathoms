"""Smoke tests do seed v1 ``asset_catalog`` (ADR-224 FU-2 PR-A; valida estrutura + cobertura mínima sem rodar Alembic; marker ``migration`` para opt-in só quando ``backend/alembic/versions/`` é tocado)."""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.migration

migration_module = importlib.import_module(
    "backend.alembic.versions.adr224_asset_catalog_lastro_moeda"
)


class TestAssetCatalogSeedV1:
    def test_seed_loads_from_yaml(self):
        rows = migration_module._load_seed_v1()
        assert len(rows) >= 20, "V1 deve cobrir mínimo de ETFs + fundos + stables"

    def test_all_rows_have_required_fields(self):
        rows = migration_module._load_seed_v1()
        for row in rows:
            assert "asset_class" in row
            assert "lastro_moeda" in row
            assert row["lastro_moeda"] in ("BRL", "USD", "EUR", "MIXED", "OTHER")
            assert (
                row.get("ticker") is not None
                or row.get("cnpj") is not None
                or row.get("match_keyword") is not None
            ), f"Row deve ter pelo menos um matcher: {row!r}"

    def test_seed_includes_canonical_etfs_b3_usd(self):
        rows = migration_module._load_seed_v1()
        tickers = {r.get("ticker") for r in rows if r.get("ticker")}
        # financial-planner FU-2.Q1 — cobertura mínima
        for expected in ("IVVB11", "BIVB11", "ACWI11", "NASD11", "SPXI11"):
            assert expected in tickers, f"ETF B3 USD canônico ausente: {expected}"

    def test_seed_includes_stablecoins(self):
        rows = migration_module._load_seed_v1()
        tickers = {r.get("ticker") for r in rows if r.get("ticker")}
        for expected in ("USDT", "USDC", "DAI"):
            assert expected in tickers, f"Stablecoin canônica ausente: {expected}"

    def test_seed_includes_fund_keyword_families(self):
        rows = migration_module._load_seed_v1()
        kws = {r.get("match_keyword") for r in rows if r.get("match_keyword")}
        assert any("btg" in (k or "") for k in kws), "BTG Global família ausente"
        assert any("xp global" in (k or "") for k in kws), "XP Global família ausente"

    def test_etfs_b3_usd_marked_internacional(self):
        rows = migration_module._load_seed_v1()
        ivvb = next(r for r in rows if r.get("ticker") == "IVVB11")
        assert ivvb["asset_class"] == "Internacional"
        assert ivvb["lastro_moeda"] == "USD"

    def test_stablecoins_marked_cripto(self):
        rows = migration_module._load_seed_v1()
        usdt = next(r for r in rows if r.get("ticker") == "USDT")
        assert usdt["asset_class"] == "Cripto"
        assert usdt["lastro_moeda"] == "USD"

    def test_no_duplicate_tickers_in_seed(self):
        rows = migration_module._load_seed_v1()
        tickers = [r.get("ticker") for r in rows if r.get("ticker")]
        assert len(tickers) == len(set(tickers)), "Duplicate ticker no seed v1"

    def test_no_duplicate_keywords_in_seed(self):
        rows = migration_module._load_seed_v1()
        kws = [r.get("match_keyword") for r in rows if r.get("match_keyword")]
        assert len(kws) == len(set(kws)), "Duplicate match_keyword no seed v1"
