"""Integração: E1.5c emite property_id quando resolver injetado (ADR-215 P2)."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext


def _build_baseline_with_imovel() -> dict:
    """Baseline schema flat `itens[]` com 1 imóvel código 12 (casa)."""
    return {
        "itens": [
            {
                "codigo": "12",
                "descricao": "CASA - RUA TASSO DA SILVEIRA, 61 - SP",
                "categoria": "imovel",
                "valor_brl": 996821.46,
                "membro": "david_robert",
                "ano": 2024,
            },
            {
                "codigo": "11",
                "descricao": "APARTAMENTO - AV PAULISTA, 1500, APT 42",
                "categoria": "imovel",
                "valor_brl": 850000.00,
                "membro": "david_robert",
                "ano": 2024,
            },
        ],
        "resumo": {
            "total_ativos": 1846821.46,
            "total_passivos": 0.0,
            "patrimonio_liquido": 1846821.46,
            "ano_referencia": 2024,
        },
    }


def _make_ctx(
    tmp_path: Path, *, with_resolver: bool
) -> tuple[WorkspaceContext, InMemoryPropertyIdentityResolver]:
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    (tmp_path / "config" / "family_members.json").write_text("{}")
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", _build_baseline_with_imovel())

    resolver = InMemoryPropertyIdentityResolver()
    ctx = WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="test-ws-001" if with_resolver else None,
        property_identity_resolver=resolver if with_resolver else None,
    )
    return ctx, resolver


def test_consolidate_enriches_imoveis_with_property_id(tmp_path):
    ctx, resolver = _make_ctx(tmp_path, with_resolver=True)

    from scripts.consolidate_baseline import main_with_store

    result = main_with_store(ctx)
    assert result["success"] is True

    consolidated = ctx.get_artifact_store().read("E1.5c", "baseline_patrimonial")
    imoveis = consolidated["imoveis_consolidados"]
    assert len(imoveis) == 2

    for e in imoveis:
        assert "property_id" in e and e["property_id"] is not None
        assert "endereco_canonical" in e
        assert "low_confidence" in e

    casa = next(e for e in imoveis if "TASSO" in e["descricao"].upper())
    assert casa["endereco_canonical"] == "tasso silveira 61"
    assert casa["low_confidence"] is False

    # 2 imóveis distintos = 2 rows em property_identity
    assert len(resolver.all()) == 2


def test_consolidate_skips_enrichment_without_resolver(tmp_path):
    """CLI legado / testes sem DB: consolidador funciona sem resolver."""
    ctx, _ = _make_ctx(tmp_path, with_resolver=False)

    from scripts.consolidate_baseline import main_with_store

    result = main_with_store(ctx)
    assert result["success"] is True

    consolidated = ctx.get_artifact_store().read("E1.5c", "baseline_patrimonial")
    imoveis = consolidated["imoveis_consolidados"]
    # codigo_rfb e ano_referencia são preenchidos pelo consolidador (P2 setup),
    # mas property_id não — resolver não foi injetado.
    for e in imoveis:
        assert "property_id" not in e
