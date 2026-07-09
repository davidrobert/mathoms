"""Testes de integração da API de Goals (ADR-073).

Focado em:
1. Felicidade de cada endpoint (compute / get / put / history)
2. 403 em acesso cross-tenant (ADR-072)
3. 404 quando workspace não tem goal ainda
4. Versionamento: PUT consecutivo fecha anterior
"""

from __future__ import annotations

import pytest

from backend.app.core.security import create_access_token
from backend.tests import factories

# ─── Helpers ────────────────────────────────────────────────────────────


async def _make_auth(db, client):
    """Cria user + workspace (com owner membership auto) + retorna
    (workspace, client_autenticado)."""
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user, ws


IF_INPUTS = {
    "renda_passiva_mensal_brl": 30000,
    "trs_pct": 5.0,
    "retorno_real_anual_pct": 6.0,
    "horizonte_anos": 15,
    "taxa_retirada_conservadora_pct": 4.0,
}


# ─── /goals/if/compute (dry-run) ─────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_if_dry_run_returns_derived(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/goals/if/compute",
        json={"inputs": IF_INPUTS},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["derived"]["if_meta_brl"] == 7_200_000.0
    assert data["derived"]["if_meta_conservadora_brl"] == 9_000_000.0
    assert data["derived"].get("aporte_mensal_com_patrimonio_atual_brl") is None
    assert data["percentual_conquistado"] is None
    assert data["faltante_brl"] is None


@pytest.mark.asyncio
async def test_compute_if_dry_run_with_patrimonio_returns_progress(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/goals/if/compute",
        json={"inputs": IF_INPUTS, "patrimonio_atual_brl": 1_800_000},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["percentual_conquistado"] == 25.0  # 1.8M de 7.2M
    assert data["faltante_brl"] == 5_400_000.0
    der = data["derived"]
    assert der["aporte_mensal_com_patrimonio_atual_brl"] is not None
    assert der["aporte_mensal_com_patrimonio_atual_brl"] < der["aporte_necessario_mensal_brl"]


@pytest.mark.asyncio
async def test_compute_if_rejects_invalid_inputs(db, client):
    _, ws = await _make_auth(db, client)
    bad = dict(IF_INPUTS, renda_passiva_mensal_brl=-1)
    resp = await client.post(f"/api/workspaces/{ws.id}/goals/if/compute", json={"inputs": bad})
    assert resp.status_code == 422


# ─── /goals/if (GET + PUT) ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_if_goal_404_when_not_configured(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.get(f"/api/workspaces/{ws.id}/goals/if")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_if_goal_enriches_aporte_with_latest_report(db, client):
    _, ws = await _make_auth(db, client)
    await factories.make_if_goal(db, workspace=ws)
    await factories.make_report(db, workspace=ws, patrimonio_liquido=1_800_000.0)
    await db.commit()

    resp = await client.get(f"/api/workspaces/{ws.id}/goals/if")
    assert resp.status_code == 200
    der = resp.json()["derived"]
    assert der["aporte_mensal_com_patrimonio_atual_brl"] is not None
    assert der["aporte_mensal_com_patrimonio_atual_brl"] < der["aporte_necessario_mensal_brl"]


@pytest.mark.asyncio
async def test_put_if_goal_creates_first_version(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.put(
        f"/api/workspaces/{ws.id}/goals/if",
        json={"inputs": IF_INPUTS, "notes": "configuração inicial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == ws.id
    assert data["derived"]["if_meta_brl"] == 7_200_000.0
    assert data["meta_version"] == 1
    assert data["effective_to"] is None
    assert data["notes"] == "configuração inicial"


@pytest.mark.asyncio
async def test_put_if_goal_twice_closes_previous_version(db, client):
    _, ws = await _make_auth(db, client)
    # v1
    r1 = await client.put(
        f"/api/workspaces/{ws.id}/goals/if",
        json={"inputs": dict(IF_INPUTS, renda_passiva_mensal_brl=20000)},
    )
    assert r1.status_code == 200

    # v2 (edita renda)
    r2 = await client.put(
        f"/api/workspaces/{ws.id}/goals/if",
        json={"inputs": dict(IF_INPUTS, renda_passiva_mensal_brl=30000)},
    )
    assert r2.status_code == 200
    assert r2.json()["derived"]["if_meta_brl"] == 7_200_000.0

    # history deve ter 2 entradas — vigente primeiro
    rh = await client.get(f"/api/workspaces/{ws.id}/goals/if/history")
    assert rh.status_code == 200
    hist = rh.json()
    assert hist["total"] == 2
    assert hist["goals"][0]["effective_to"] is None
    assert hist["goals"][0]["derived"]["if_meta_brl"] == 7_200_000.0
    assert hist["goals"][1]["effective_to"] is not None


# ─── Multi-tenant isolation (ADR-072) ───────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_get_returns_403(db, client):
    """User A tenta ler goal de workspace B — recebe 403 (nem 404, para
    evitar enumeração)."""
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await factories.make_if_goal(db, workspace=ws_b)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"

    resp = await client.get(f"/api/workspaces/{ws_b.id}/goals/if")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_put_returns_403(db, client):
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"

    resp = await client.put(f"/api/workspaces/{ws_b.id}/goals/if", json={"inputs": IF_INPUTS})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(db, client):
    # Sem token
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()

    resp = await client.get(f"/api/workspaces/{ws.id}/goals/if")
    assert resp.status_code in (401, 403)  # httpx/FastAPI retorna 403 se Bearer ausente


@pytest.mark.asyncio
async def test_workspace_id_does_not_exist_returns_403(db, client):
    """Workspace ID fake — retorna 403 (não 404), para não vazar
    existência de IDs alheios."""
    user = await factories.make_user(db)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get("/api/workspaces/00000000-0000-0000-0000-000000000000/goals/if")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_history_is_workspace_scoped(db, client):
    """Garantir que history NÃO mostra goals de outros workspaces."""
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await factories.make_if_goal(db, workspace=ws_a, renda_passiva_mensal_brl=10000)
    await factories.make_if_goal(db, workspace=ws_b, renda_passiva_mensal_brl=50000)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"
    resp = await client.get(f"/api/workspaces/{ws_a.id}/goals/if/history")
    assert resp.status_code == 200
    hist = resp.json()
    assert hist["total"] == 1
    assert hist["goals"][0]["derived"]["if_meta_brl"] == 2_400_000.0


# ─── /goals/alocacao — flip v2 (ADR-141 emenda, A12.alocacao-v2 PR4) ───

ALOCACAO_V2_INPUTS = {
    "rf_pos_pct": 20,
    "rf_pre_pct": 10,
    "rf_ipca_pct": 10,
    "acoes_br_pct": 25,
    "acoes_int_pct": 15,
    "fiis_pct": 10,
    "caixa_pct": 10,
    "rebalanceamento_modo": "por_aporte",
}
ALOCACAO_V1_ROW = {
    "renda_fixa_pct": 40,
    "acoes_pct": 30,
    "imoveis_reits_pct": 20,
    "liquidez_usd_pct": 10,
}
ALOCACAO_ORPHAN_ROW = {"rf_pct": 40, "rv_pct": 40, "alternativos_pct": 20}


async def _seed_alocacao_row(db, ws_id, inputs, derived):
    """Grava row de alocação direto no repo (bypassa DTO) p/ testar conversão on-read."""
    from backend.app.repositories.goal_repository import GoalRepository

    await GoalRepository(db).create_new_version(
        ws_id,
        "ALOCACAO_ALVO",
        params_json={"inputs": inputs, "meta_version": 1},
        derived_json=derived,
    )
    await db.commit()


@pytest.mark.asyncio
async def test_put_alocacao_v2_roundtrip(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.put(
        f"/api/v1/workspaces/{ws.id}/goals/alocacao", json={"inputs": ALOCACAO_V2_INPUTS}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta_version"] == 2
    assert body["converted_from"] is None
    assert body["derived"]["soma_percentuais"] == 100
    read = await client.get(f"/api/v1/workspaces/{ws.id}/goals/alocacao")
    assert read.json()["inputs"]["caixa_pct"] == 10


@pytest.mark.asyncio
async def test_put_alocacao_payload_v1_rejeitado_422(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.put(
        f"/api/v1/workspaces/{ws.id}/goals/alocacao", json={"inputs": ALOCACAO_V1_ROW}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_alocacao_soma_diferente_de_100_rejeitada(db, client):
    _, ws = await _make_auth(db, client)
    quebrado = dict(ALOCACAO_V2_INPUTS, caixa_pct=50)
    resp = await client.put(f"/api/v1/workspaces/{ws.id}/goals/alocacao", json={"inputs": quebrado})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_alocacao_row_v1_converte_on_read(db, client):
    # Row legada v1 → GET responde v2 com converted_from="1" e is_template=True.
    _, ws = await _make_auth(db, client)
    await _seed_alocacao_row(db, ws.id, ALOCACAO_V1_ROW, {"soma_percentuais": 100.0})
    body = (await client.get(f"/api/v1/workspaces/{ws.id}/goals/alocacao")).json()
    assert body["converted_from"] == "1"
    assert body["is_template"] is True
    assert body["inputs"]["rf_pos_pct"] == 20
    assert body["inputs"]["acoes_int_pct"] == 7
    assert body["inputs"]["caixa_pct"] == 3


@pytest.mark.asyncio
async def test_get_alocacao_row_orfa_do_seed_nao_quebra_mais(db, client):
    # Regressão do bug vivo pré-PR4: shape órfão do seed quebrava o GET (500).
    _, ws = await _make_auth(db, client)
    await _seed_alocacao_row(db, ws.id, ALOCACAO_ORPHAN_ROW, {})
    body = (await client.get(f"/api/v1/workspaces/{ws.id}/goals/alocacao")).json()
    assert body["converted_from"] == "orphan"
    assert body["derived"]["soma_percentuais"] == 100


@pytest.mark.asyncio
async def test_history_alocacao_mista_responde_tudo_v2(db, client):
    # Conversão universal no history (ADR-141 emenda item 6): v1 + v2 → tudo v2.
    _, ws = await _make_auth(db, client)
    await _seed_alocacao_row(db, ws.id, ALOCACAO_V1_ROW, {"soma_percentuais": 100.0})
    put = await client.put(
        f"/api/v1/workspaces/{ws.id}/goals/alocacao", json={"inputs": ALOCACAO_V2_INPUTS}
    )
    assert put.status_code == 200
    goals = (await client.get(f"/api/v1/workspaces/{ws.id}/goals/alocacao/history")).json()["goals"]
    assert len(goals) == 2
    assert {g["converted_from"] for g in goals} == {None, "1"}
    assert all("rf_pos_pct" in g["inputs"] for g in goals)


@pytest.mark.asyncio
async def test_compute_alocacao_v2_dry_run(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(
        f"/api/v1/workspaces/{ws.id}/goals/alocacao/compute", json={"inputs": ALOCACAO_V2_INPUTS}
    )
    assert resp.status_code == 200
    assert resp.json()["valido"] is True
