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
    assert (
        der["aporte_mensal_com_patrimonio_atual_brl"]
        < der["aporte_necessario_mensal_brl"]
    )


@pytest.mark.asyncio
async def test_compute_if_rejects_invalid_inputs(db, client):
    _, ws = await _make_auth(db, client)
    bad = dict(IF_INPUTS, renda_passiva_mensal_brl=-1)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/goals/if/compute", json={"inputs": bad}
    )
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
    assert (
        der["aporte_mensal_com_patrimonio_atual_brl"]
        < der["aporte_necessario_mensal_brl"]
    )


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

    resp = await client.put(
        f"/api/workspaces/{ws_b.id}/goals/if", json={"inputs": IF_INPUTS}
    )
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

    resp = await client.get(
        "/api/workspaces/00000000-0000-0000-0000-000000000000/goals/if"
    )
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
