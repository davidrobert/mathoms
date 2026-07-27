"""Regressão RV2-08: binding de campos da posição E4 na exposição cambial V2.

Antes do fix, `_aggregate_positions` lia `valor`/`valor_31_12` (posições E4 usam
`valor_atual`) → 0 para toda posição; `_build_asset_query` lia `ticker`/`codigo`
(posições usam `ticker_norm`) → o match de catalog nunca disparava. Efeito: todo
ativo internacional sumia da exposição cambial. Conformidade ADR-224 §3.
"""

from __future__ import annotations

from decimal import Decimal

from backend.app.application.exposicao_cambial_v2 import (
    _aggregate_positions,
    _build_asset_query,
)
from backend.app.services.lastro_resolver import CatalogEntry


def test_build_asset_query_usa_ticker_norm_e_nome():
    q = _build_asset_query({"ticker_norm": "IVVB11", "nome": "iShares SP500", "tipo": "etf"})
    assert q.ticker == "IVVB11"  # antes lia 'ticker'/'codigo' (ausentes) → None
    assert q.descricao == "iShares SP500"  # nome-first
    assert q.asset_class_fallback  # derivado (não mais hardcoded 'Outros')


def test_aggregate_le_valor_atual_e_resolve_catalog_usd():
    catalog = [
        CatalogEntry(
            ticker="IVVB11",
            cnpj=None,
            match_keyword=None,
            asset_class="Internacional",
            lastro_moeda="USD",
        )
    ]
    por_moeda, contribuintes = _aggregate_positions(
        [{"ticker_norm": "IVVB11", "nome": "iShares SP500", "tipo": "etf", "valor_atual": "5000"}],
        catalog,
        [],
    )
    assert por_moeda.get("USD") == Decimal("5000")  # antes: 0 (valor ausente) → vazio
    assert len(contribuintes) == 1
    assert contribuintes[0].moeda == "USD"


def test_aggregate_ignora_posicao_valor_zero():
    por_moeda, contribuintes = _aggregate_positions(
        [{"ticker_norm": "IVVB11", "nome": "x", "valor_atual": "0"}], [], []
    )
    assert por_moeda == {}
    assert contribuintes == []
