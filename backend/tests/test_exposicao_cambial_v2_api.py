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


# Até 2026-08 esta fixture fabricava `patrimonio_full`/`investimentos_atuais`, nomes de
# variável interna do domínio. Nenhum artefato jamais os teve: a fixture e o código
# compartilhavam a mesma crença errada, e a suíte ficou verde três meses sobre um
# endpoint que devolvia zero em produção. `posicoes` não tem onde morar — o E5 publica
# agregados, não posições individuais (elas vivem no E4); o parâmetro segue na
# assinatura para os testes que documentam a lacuna.
def _e5_payload(
    *,
    posicoes: list[dict],
    caixa_detalhes: list[dict],
    investivel: Decimal,
) -> dict:
    """Shape REAL do artefato E5 — as chaves que `e5_serialization` emite."""
    payload = {
        "patrimonio": {
            "caixa_detalhes": caixa_detalhes,
            # str porque JSON column não serializa Decimal nativamente; _to_decimal lê string corretamente
            "investivel_financeiro": str(investivel),
        },
        "investimentos": {"total_financeiro": str(investivel), "tabela_classes": []},
    }
    assert "dados" not in payload["investimentos"], (
        "o E5 não publica posições individuais — se passou a publicar, ligue o braço de "
        "ativos do V2 em vez de reintroduzir a fixture fictícia"
    )
    return payload


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
async def test_sem_artefato_e5_declara_falta_de_base_e_nao_zero(auth_client: AsyncClient):
    """Sem artefato não há exposição conhecida — e zero seria uma afirmação falsa."""
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    assert resp.status_code == 200
    data = resp.json()
    assert data["base_disponivel"] is False
    assert data["total_brl"] is None
    assert data["pct_investivel_financeiro"] is None
    assert data["tier"] is None
    assert data["por_moeda"] == []
    assert data["ativos_contribuintes"] == []
    assert data["source_run_id"] is None


async def _seed_run_com_caixa(db, ws_id: str, quantia: str) -> PipelineArtifact:
    """Um run com uma única conta em USD da quantia pedida."""
    caixa = [{"conta": "Wise USD", "moeda": "USD", "valor_brl": quantia, "saldo_original": "1"}]
    payload = _e5_payload(posicoes=[], caixa_detalhes=caixa, investivel=Decimal("500000"))
    return await _seed_e5_artifact(db, ws_id, payload)


async def _seed_report(db, ws_id: str, run_id) -> str:
    from backend.app.models.report import Report

    report = Report(workspace_id=ws_id, pipeline_run_id=run_id, title="Relatório antigo")
    db.add(report)
    await db.commit()
    return report.id


# Medido em 2026-08-12: sem pinagem, 83 de 84 relatórios exibiam a exposição de outro
# momento patrimonial dentro de um documento que promete ser foto datada.
@pytest.mark.asyncio
async def test_card_usa_o_run_do_relatorio_e_nao_o_artefato_mais_recente(
    auth_client: AsyncClient, db
):
    """Dois runs no mesmo workspace: pedir o relatório antigo devolve o número antigo."""
    antigo = await _seed_run_com_caixa(db, auth_client.ws_id, "10000")
    await _seed_run_com_caixa(db, auth_client.ws_id, "90000")
    report_id = await _seed_report(db, auth_client.ws_id, antigo.pipeline_run_id)

    url = f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial"
    pinado = (await auth_client.get(f"{url}?report_id={report_id}")).json()
    assert pinado["total_brl"] == "10000.00", "pinado deve trazer o run do relatório pedido"
    assert pinado["source_run_id"] == str(antigo.pipeline_run_id)

    # Sem report_id, resolve pelo relatório mais recente — nunca pelo artefato mais recente.
    sem_pin = (await auth_client.get(url)).json()
    assert sem_pin["source_run_id"] == str(antigo.pipeline_run_id)


@pytest.mark.asyncio
async def test_denominador_zero_nao_vira_zero_por_cento(auth_client: AsyncClient, db):
    """Com caixa em USD mas sem investível, o card não pode exibir valor cheio ao lado
    de '0,0% · sub-alocado' — sem denominador não há percentual, logo não há veredito."""
    payload = _e5_payload(
        posicoes=[],
        caixa_detalhes=[
            {"conta": "Wise USD", "moeda": "USD", "valor_brl": 50000.0, "saldo_original": 10000.0}
        ],
        investivel=Decimal("0"),
    )
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    data = resp.json()
    assert data["base_disponivel"] is False
    assert data["pct_investivel_financeiro"] is None
    assert data["tier"] is None


@pytest.mark.asyncio
async def test_chave_de_patrimonio_ausente_nao_vira_zero(auth_client: AsyncClient, db):
    """Drift de shape (a classe de bug original) tem que degradar, não afirmar ausência."""
    await _seed_e5_artifact(db, auth_client.ws_id, {"investimentos": {}, "score": 70})
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    data = resp.json()
    assert data["base_disponivel"] is False
    assert data["total_brl"] is None


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
async def test_braco_de_ativos_nao_chega_ao_endpoint_enquanto_e5_nao_publica_posicoes(
    auth_client: AsyncClient, db
):
    """Tripwire: nenhuma posição alcança o endpoint — o E5 publica agregados."""
    # Catálogo e override resolvem lastro (coberto em unidade no
    # `test_exposicao_cambial_v2_binding.py`), mas o braço nunca é alimentado. Este teste
    # QUEBRA quando a fonte for ligada ao artefato E4 — quebrar é o ponto: força quem
    # ligar a asserir o novo comportamento em vez de herdar cobertura que media o vazio.
    await _seed_catalog_entry(db, ticker="IVVB11", lastro_moeda="USD")
    payload = _e5_payload(posicoes=[], caixa_detalhes=[], investivel=Decimal("500000"))
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    assert resp.status_code == 200
    data = resp.json()
    assert data["base_disponivel"] is True
    assert data["ativos_contribuintes"] == []
    assert data["total_brl"] == "0.00"


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
