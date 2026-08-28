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
# A40.l80: o card só julga faixa com TODOS os componentes apurados — o mesmo
# predicado do `_tier` do E5. Sem isso, `indeterminado`.
# A40.l80: o bloco vem do PRODUTOR, não escrito à mão. Antes ele fixava
# `valor_brl: 0.0` e não trazia `por_moeda` — estado que produção nunca emite, e que
# escondia a divergência de 6× entre o E5 e este card (a linha `moeda_estrangeira_irpf`
# nasce com `moeda="BRL"` e o card a descartava). Com a fixture fabricada, nenhum dos
# testes caía.
#
# `cobertura` continua sobrescrita à mão porque o produtor fixa
# `carteira_lastro_estrangeiro` em `indeterminado` incondicionalmente (ADR-403 §D1): sem o
# override, os ramos de tier `verde`/`amarelo`/`vermelho` seriam inalcançáveis. Eles
# testam regime que produção HOJE não alcança — está declarado, não é acidente.
def _componentes(cobertura: str, caixa_detalhes: list[dict], investivel: Decimal) -> dict:
    from pipeline.domain.services.exposicao_cambial_analyzer import compute_exposicao_cambial

    publicado = compute_exposicao_cambial(
        caixa_detalhes=caixa_detalhes,
        investimentos_atuais=None,
        investivel_financeiro=float(investivel),
    ).to_dict()
    for componente in publicado["componentes"].values():
        componente["cobertura"] = cobertura
    return publicado


def _patrimonio(caixa_detalhes: list[dict], investivel: Decimal, serie_corrente: bool) -> dict:
    # str porque JSON column não serializa Decimal nativamente; _to_decimal lê string corretamente
    out = {"caixa_detalhes": caixa_detalhes, "investivel_financeiro": str(investivel)}
    if serie_corrente:
        out["base_versao"] = 1
    return out


def _e5_payload(
    *,
    posicoes: list[dict],
    caixa_detalhes: list[dict],
    investivel: Decimal,
    cobertura: str = "apurado",
    serie_corrente: bool = True,
) -> dict:
    """Shape REAL do artefato E5 — as chaves que `e5_serialization` emite."""
    payload = {
        "patrimonio": _patrimonio(caixa_detalhes, investivel, serie_corrente),
        "investimentos": {"total_financeiro": str(investivel), "tabela_classes": []},
        "exposicao_cambial": _componentes(cobertura, caixa_detalhes, investivel),
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


# A linha do IRPF: já convertida, logo `moeda == "BRL"` — e era por ela que o card divergia.
_CAIXA_COM_IRPF = [
    {"conta": "Wise USD", "moeda": "USD", "valor_brl": 100000.0},
    {
        "tipo": "moeda_estrangeira_irpf",
        "conta": "deposito em dolar",
        "moeda": "BRL",
        "valor_brl": 500000.0,
    },
]


def _PAYLOAD_COM_IRPF() -> dict:
    return _e5_payload(posicoes=[], caixa_detalhes=_CAIXA_COM_IRPF, investivel=Decimal("5000000"))


# A40.l80 §Prova de fecho (P1): nenhum teste alimentava linha `moeda_estrangeira_irpf`, e
# era por ela que o card divergia do produtor em 6×. `moeda` é UNIDADE DE MEDIDA
# ([[ADR-245]] §L3) — a linha nasce com `"BRL"` porque o saldo já vem convertido —, e o
# card a classificava como "não é exposição".
@pytest.mark.asyncio
async def test_card_publica_o_MESMO_numero_que_o_produtor(auth_client: AsyncClient, db):
    """Paridade E5 ↔ card sobre a linha que o card descartava."""
    from pipeline.domain.services.exposicao_cambial_analyzer import compute_exposicao_cambial

    do_produtor = compute_exposicao_cambial(
        caixa_detalhes=_CAIXA_COM_IRPF, investimentos_atuais=None, investivel_financeiro=5_000_000.0
    ).to_dict()
    await _seed_e5_artifact(db, auth_client.ws_id, _PAYLOAD_COM_IRPF())

    data = (
        await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    ).json()

    assert Decimal(data["total_brl"]) == Decimal(str(do_produtor["total_brl"]))
    assert data["pct_investivel_financeiro"] == do_produtor["pct_investivel_financeiro"]
    assert {pm["moeda"] for pm in data["por_moeda"]} == {
        linha["moeda"] for linha in do_produtor["por_moeda"]
    }


@pytest.mark.asyncio
async def test_a_linha_do_irpf_entra_no_numerador(auth_client: AsyncClient, db):
    """Sem ela o card publicaria 2,0% onde o produtor publica 12,0% — 6×, subdeclarando."""
    await _seed_e5_artifact(db, auth_client.ws_id, _PAYLOAD_COM_IRPF())

    data = (
        await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    ).json()

    assert data["pct_investivel_financeiro"] == 12.0, "a linha do IRPF saiu do numerador"
    assert Decimal(data["total_brl"]) == Decimal("600000.00")


@pytest.mark.asyncio
# O braço nunca é alimentado: `_posicoes_do_payload` lê `investimentos["dados"]`, chave que
# o schema de `investimentos` NÃO tem, então ele devolve `[]` sempre.
#
# A DECISÃO QUE ESPERA QUEM QUEBRAR ESTE TESTE ([[ADR-403]] §D3 · [[ADR-412]] §E10): desde o
# #1794 a perna de caixa é CONSUMIDA do artefato, que é v1 (só caixa FX). Ligar a perna de
# posições soma ao total algo que a v1 exclui — o card vira produtor de definição NOVA. Ou
# ele declara `definicao_versao=2` e ganha o de-dup caixa↔carteira que a §D4 torna
# obrigatório, ou a perna não entra no total. O que não existe é a terceira opção
# silenciosa: somar as duas sob o marcador do produtor, que rotula a computação DELE.
async def test_braco_de_ativos_nao_chega_ao_endpoint_enquanto_e5_nao_publica_posicoes(
    auth_client: AsyncClient, db
):
    """Tripwire: nenhuma posição alcança o endpoint — quebrar é o ponto."""
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


@pytest.mark.asyncio
async def test_card_suprime_veredito_quando_o_e5_recusa(auth_client: AsyncClient, db):
    """A40.l80: o card publicava faixa na mesma tela em que o relatório dizia
    `indeterminado`. Mata: remover a perna de cobertura de `_tier`."""
    payload = _e5_payload(
        posicoes=[],
        caixa_detalhes=[
            {"conta": "Wise USD", "moeda": "USD", "valor_brl": 60000.0, "saldo_original": 12000.0},
        ],
        investivel=Decimal("500000"),
        cobertura="indeterminado",
    )
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    data = (
        await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    ).json()

    assert data["tier"] == "indeterminado"
    # A MEDIDA continua publicada — suprime-se o veredito, nunca o número.
    assert data["total_brl"] is not None
    assert data["pct_investivel_financeiro"] is not None


@pytest.mark.asyncio
async def test_card_degrada_em_artefato_sem_base_versao(auth_client: AsyncClient, db):
    """Mata: recompor artefato de base antiga com código novo — o híbrido sem
    rótulo da [[ADR-412]] §D8. Ausência é "não sei", nunca "série corrente"."""
    payload = _e5_payload(
        posicoes=[],
        caixa_detalhes=[
            {"conta": "Wise USD", "moeda": "USD", "valor_brl": 60000.0, "saldo_original": 12000.0},
        ],
        investivel=Decimal("500000"),
        serie_corrente=False,
    )
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    data = (
        await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    ).json()

    assert data["tier"] == "indeterminado"


@pytest.mark.asyncio
async def test_card_le_a_base_declarada_e_nao_o_campo_legado(auth_client: AsyncClient, db):
    """Mata: recompor o denominador em vez de ler `patrimonio.bases`, o que faria
    o card divergir do relatório na mesma tela."""
    payload = _e5_payload(
        posicoes=[],
        caixa_detalhes=[
            {"conta": "Wise USD", "moeda": "USD", "valor_brl": 50000.0, "saldo_original": 10000.0},
        ],
        investivel=Decimal("250000"),
    )
    payload["patrimonio"]["bases"] = {
        "carteira_financeira_familia": {"termos": [], "valor_brl": 500000.0}
    }
    await _seed_e5_artifact(db, auth_client.ws_id, payload)
    data = (
        await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    ).json()

    # 50k sobre a base DECLARADA (500k) = 10%, não sobre o legado (250k) = 20%.
    assert data["pct_investivel_financeiro"] == 10.0
