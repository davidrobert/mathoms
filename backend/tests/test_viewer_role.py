"""Role matrix — garante que `viewer` é read-only nos endpoints F8+.

Escopo V1: só testamos `/goals/if` — é o único endpoint tenant-scoped F8+
hoje. À medida que novos endpoints F8+ chegarem (ou endpoints legados
migrarem), adicionar casos aqui.

Endpoints legados (pré-F8) ainda usam `_get_workspace(user)` e não passam
por `get_current_workspace`/`require_write_role`. Eles continuam filtrando
por `owner_id` e portanto um `viewer` nem consegue chegar lá. Quando
migrados, os testes correspondentes devem aparecer nesta matriz.
"""

from __future__ import annotations

import pytest

from backend.app.core.security import create_access_token
from backend.tests import factories


async def _viewer_setup(db, client):
    """Cria workspace onde `viewer_user` tem role viewer e `owner_user`
    é owner. Retorna (viewer_user, owner_user, ws)."""
    owner_user = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner_user)
    viewer_user = await factories.make_user(db, email="viewer@test.com")
    await factories.make_workspace_member(
        db, workspace=ws, user=viewer_user, role="viewer"
    )
    await db.commit()
    return viewer_user, owner_user, ws


IF_INPUTS = {
    "renda_passiva_mensal_brl": 30000,
    "trs_pct": 5.0,
    "retorno_real_anual_pct": 6.0,
    "horizonte_anos": 15,
    "taxa_retirada_conservadora_pct": 4.0,
}


# ─── Goals — viewer pode ler, não pode escrever ────────────────────


@pytest.mark.asyncio
async def test_viewer_can_read_goal_history(db, client):
    viewer, owner, ws = await _viewer_setup(db, client)
    await factories.make_if_goal(db, workspace=ws)
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(viewer.id)}"
    resp = await client.get(f"/api/workspaces/{ws.id}/goals/if/history")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_put_goal(db, client):
    """Endpoints de ESCRITA rejeitam viewer com 403. F9.3 aplicou
    `require_write_role` em `PUT /goals/if`."""
    viewer, owner, ws = await _viewer_setup(db, client)
    client.headers["Authorization"] = f"Bearer {create_access_token(viewer.id)}"
    resp = await client.put(
        f"/api/workspaces/{ws.id}/goals/if", json={"inputs": IF_INPUTS}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_member_can_put_goal(db, client):
    """Sanity check do outro lado da matriz: `member` (não-viewer) ainda
    consegue editar. Evita regressão onde a dependency recusa todos."""
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    mem = await factories.make_user(db, email="mem@test.com")
    await factories.make_workspace_member(
        db, workspace=ws, user=mem, role="member"
    )
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(mem.id)}"
    resp = await client.put(
        f"/api/workspaces/{ws.id}/goals/if", json={"inputs": IF_INPUTS}
    )
    assert resp.status_code == 200


# ─── Membros — viewer pode listar, não pode gerenciar ───────────────


@pytest.mark.asyncio
async def test_viewer_cannot_invite(db, client):
    viewer, owner, ws = await _viewer_setup(db, client)
    client.headers["Authorization"] = f"Bearer {create_access_token(viewer.id)}"
    resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "x@test.com", "role": "viewer"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_remove_members(db, client):
    viewer, owner, ws = await _viewer_setup(db, client)
    victim = await factories.make_user(db, email="victim@test.com")
    await factories.make_workspace_member(
        db, workspace=ws, user=victim, role="member"
    )
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(viewer.id)}"
    resp = await client.delete(f"/api/workspaces/{ws.id}/members/{victim.id}")
    assert resp.status_code == 403


# ─── Non-member continua 403 (sanity check do tenancy) ─────────────


@pytest.mark.asyncio
async def test_outsider_receives_403(db, client):
    _, _, ws = await _viewer_setup(db, client)
    outsider = await factories.make_user(db, email="outsider@test.com")
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(outsider.id)}"
    resp = await client.get(f"/api/workspaces/{ws.id}/members")
    assert resp.status_code == 403
