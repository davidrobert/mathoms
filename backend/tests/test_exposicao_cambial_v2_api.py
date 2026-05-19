"""Integration tests do endpoint Exposição Cambial V2 (ADR-224 PR-B; valida read-time + catalog seed v1 + workspace override + tier thresholds)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from backend.app.models import (
    AssetCatalog,
    PipelineArtifact,
    PipelineRun,
    WorkspaceAssetOverride,
)


def _e5_payload(
    *,
    posicoes: list[dict],
    caixa_detalhes: list[dict],
    investivel: Decimal,
) -> dict:
    return {
        "patrimonio_full": {
            "caixa_detalhes": caixa_detalhes,
            # str porque JSON column não serializa Decimal nativamente; _to_decimal lê string corretamente
            "investivel_financeiro": str(investivel),
        },
        "investimentos_atuais": {"dados": posicoes},
    }


def _pos_ivvb11(montante: Decimal) -> dict:
    return {
        "ticker": "IVVB11",
        "descricao": "IVVB11",
        "valor": str(montante),
        "tipo": "Internacional",
        "classe": "Internacional",
    }


def _caixa_usd(conta: str, montante: Decimal) -> dict:
    return {"conta": conta, "moeda": "USD", "valor_brl": str(montante), "saldo_original": "0"}


async def _seed_e5_artifact(db, workspace_id: str, payload: dict) -> PipelineArtifact:
    run = PipelineRun(
        workspace_id=workspace_id,
        status="success",
    )
    db.add(run)
    await db.flush()
    art = PipelineArtifact(
        workspace_id=workspace_id,
        pipeline_run_id=run.id,
        stage="analyze_finances",
        artifact_key="analise_financeira",
        content_json=payload,
    )
    db.add(art)
    await db.commit()
    return art


async def _seed_override(db, workspace_id: str, match_kind: str, key: str, moeda: str) -> None:
    override = WorkspaceAssetOverride(
        workspace_id=workspace_id,
        match_kind=match_kind,
        asset_match_key=key,
        lastro_moeda=moeda,
        override_source="user_manual",
    )
    db.add(override)
    await db.commit()


async def _seed_catalog_entry(db, *, ticker: str, lastro_moeda: str = "USD") -> None:
    """Seed direto na tabela (test DB usa Base.metadata.create_all, sem rodar seed da migration)."""
    entry = AssetCatalog(
        catalog_version=1,
        ticker=ticker,
        cnpj=None,
        match_keyword=None,
        asset_class="Internacional",
        lastro_moeda=lastro_moeda,
        lastro_source="catalog",
    )
    db.add(entry)
    await db.commit()


@pytest.mark.asyncio
async def test_exposicao_cambial_empty_when_no_e5_artifact(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "empty"
    assert data["total_brl"] == "0.00"
    assert data["por_moeda"] == []
    assert data["ativos_contribuintes"] == []
    assert data["source_run_id"] is None


@pytest.mark.asyncio
async def test_exposicao_cambial_aggregates_caixa_estrangeira(auth_client: AsyncClient, db):
    payload = _e5_payload(
        posicoes=[],
        caixa_detalhes=[
            {"conta": "Wise USD", "moeda": "USD", "valor_brl": 50000.0, "saldo_original": 10000.0},
            {"conta": "Itaú BRL", "moeda": "BRL", "valor_brl": 100000.0},
        ],
        investivel=Decimal("500000"),
    )
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_brl"] == "50000.00"
    assert data["pct_investivel_financeiro"] == 10.0
    assert data["tier"] == "verde"  # 10% bate threshold
    moedas = {pm["moeda"]: pm["valor_brl"] for pm in data["por_moeda"]}
    assert moedas == {"USD": "50000.00"}


@pytest.mark.asyncio
async def test_exposicao_cambial_aggregates_ativos_via_catalog_seed(auth_client: AsyncClient, db):
    # test DB usa metadata.create_all (sem rodar seed da migration); precisa seed explícito
    await _seed_catalog_entry(db, ticker="IVVB11", lastro_moeda="USD")
    payload = _e5_payload(
        posicoes=[_pos_ivvb11(Decimal("75000"))], caixa_detalhes=[], investivel=Decimal("500000")
    )
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_brl"] == "75000.00"
    assert any(pm["moeda"] == "USD" for pm in data["por_moeda"])
    ativo = data["ativos_contribuintes"][0]
    assert ativo["moeda"] == "USD"
    assert ativo["lastro_source"] == "catalog"


@pytest.mark.asyncio
async def test_exposicao_cambial_workspace_override_wins_over_catalog(auth_client: AsyncClient, db):
    # User declara IVVB11 como BRL (override vence catalog USD)
    await _seed_catalog_entry(db, ticker="IVVB11", lastro_moeda="USD")
    await _seed_override(db, auth_client.ws_id, "ticker", "IVVB11", "BRL")
    payload = _e5_payload(
        posicoes=[_pos_ivvb11(Decimal("50000"))], caixa_detalhes=[], investivel=Decimal("500000")
    )
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    assert resp.status_code == 200
    data = resp.json()
    # BRL não conta como exposição cambial — total = 0
    assert data["total_brl"] == "0.00"
    assert data["tier"] == "empty"


@pytest.mark.asyncio
async def test_exposicao_cambial_tier_amarelo_5_to_10_pct(auth_client: AsyncClient, db):
    # 7% exposição → amarelo
    payload = _e5_payload(
        posicoes=[],
        caixa_detalhes=[
            {"conta": "Wise USD", "moeda": "USD", "valor_brl": 35000.0, "saldo_original": 7000.0},
        ],
        investivel=Decimal("500000"),
    )
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    assert resp.status_code == 200
    data = resp.json()
    assert 5.0 <= data["pct_investivel_financeiro"] < 10.0
    assert data["tier"] == "amarelo"


@pytest.mark.asyncio
async def test_exposicao_cambial_tier_vermelho_below_5_pct(auth_client: AsyncClient, db):
    payload = _e5_payload(
        posicoes=[],
        caixa_detalhes=[
            {"conta": "Wise USD", "moeda": "USD", "valor_brl": 10000.0, "saldo_original": 2000.0},
        ],
        investivel=Decimal("500000"),
    )
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pct_investivel_financeiro"] < 5.0
    assert data["tier"] == "vermelho"
