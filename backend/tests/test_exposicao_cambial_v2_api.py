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
from backend.tests.helpers.exposicao_cambial_fixtures import (
    _caixa_usd,
    _componentes,
    _e5_payload,
    _patrimonio,
    _pos_ivvb11,
    _seed_catalog_entry,
    _seed_e5_artifact,
    _seed_override,
)


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
        # `fonte` é o que `_extract_me_caixa_from_baseline` de fato grava — sem ele a
        # fixture não reproduz o shape do produtor e a supressão não arma.
        "fonte": "baseline_irpf",
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


# A40.l80 §Prova de fecho (P2, co-design `financial-planner`): frescor mata a PRESCRIÇÃO
# DIMENSIONADA, nunca a medida. Dizer "compre R$ X" sobre saldo que veio de foto anual e
# nunca foi confirmado empurra IOF, spread e evento tributário; dizer "confirme o saldo"
# custa uma conferência de extrato. A medida sobrevive porque suprimi-la faria o card
# afirmar ausência de exposição — o defeito que `_sem_base_response` já documenta.
@pytest.mark.asyncio
async def test_foto_anual_no_numerador_suprime_o_ALVO_e_preserva_a_medida(
    auth_client: AsyncClient, db
):
    """A prescrição dimensionada morre; `total_brl` e o pct ficam."""
    await _seed_e5_artifact(db, auth_client.ws_id, _PAYLOAD_COM_IRPF())

    data = (
        await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    ).json()

    assert data["alvo_moeda_forte_brl"] is None, "o alvo saiu sobre saldo não confirmado"
    assert data["alvo_suprimido_motivo"], "suprimir sem dizer por quê é silêncio, não ressalva"
    assert Decimal(data["total_brl"]) == Decimal("600000.00")
    assert data["pct_investivel_financeiro"] == 12.0


@pytest.mark.asyncio
async def test_sem_foto_anual_o_alvo_e_emitido(auth_client: AsyncClient, db):
    """Polaridade oposta: sem a linha do IRPF a prescrição continua — não é supressão geral."""
    caixa = [{"conta": "Wise USD", "moeda": "USD", "valor_brl": 100000.0}]
    payload = _e5_payload(posicoes=[], caixa_detalhes=caixa, investivel=Decimal("5000000"))
    await _seed_e5_artifact(db, auth_client.ws_id, payload)

    data = (
        await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/cards/exposicao-cambial")
    ).json()

    assert data["alvo_moeda_forte_brl"] is not None
    assert data["alvo_suprimido_motivo"] is None
