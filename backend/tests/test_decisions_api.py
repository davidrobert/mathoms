"""Testes de integração da API de Decisions (ADR-136).

Cobrem:
- POST cria + retorna 201 com id/status
- GET (list/byid) felizes
- PATCH atualiza campo + emite evento
- POST execute marca status + valida 422 quando já executada
- POST supersede atualiza chain
- 403 cross-tenant
"""

from __future__ import annotations

import pytest

from backend.app.core.security import create_access_token
from backend.tests import factories


async def _make_auth(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user, ws


@pytest.mark.asyncio
async def test_create_decision_returns_201(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/decisions",
        json={"code": "D01", "title": "Decisão fictícia", "amount_brl": "1000.00"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "D01"
    assert body["amount_brl"] == "1000.00"
    assert body["status"] == "Pendente"


@pytest.mark.asyncio
async def test_create_without_code_auto_generates_sequence(db, client):
    """ADR-214 — POST sem ``code`` aciona auto-gen server-side (D01, D02, ...).

    Substitui ``test_create_duplicate_returns_409`` (pré-ADR-214 client
    podia mandar code explícito e colidir; agora o caminho default é
    server-gen, e UNIQUE constraint é defesa em profundidade — não
    contrato HTTP).
    """
    _, ws = await _make_auth(db, client)
    base = f"/api/workspaces/{ws.id}/decisions"
    r1 = await client.post(base, json={"title": "A"})
    assert r1.status_code == 201, r1.text
    assert r1.json()["code"] == "D01"
    r2 = await client.post(base, json={"title": "B"})
    assert r2.status_code == 201, r2.text
    assert r2.json()["code"] == "D02"


@pytest.mark.asyncio
async def test_list_returns_total(db, client):
    _, ws = await _make_auth(db, client)
    base = f"/api/workspaces/{ws.id}/decisions"
    await client.post(base, json={"code": "D01", "title": "A"})
    await client.post(base, json={"code": "D02", "title": "B"})

    resp = await client.get(base)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert [d["code"] for d in body["decisions"]] == ["D01", "D02"]


@pytest.mark.asyncio
async def test_get_by_id_404_for_unknown(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.get(
        f"/api/workspaces/{ws.id}/decisions/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_updates_title(db, client):
    _, ws = await _make_auth(db, client)
    create_resp = await client.post(
        f"/api/workspaces/{ws.id}/decisions",
        json={"code": "D01", "title": "Antigo"},
    )
    decision_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/workspaces/{ws.id}/decisions/{decision_id}",
        json={"title": "Novo"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Novo"


@pytest.mark.asyncio
async def test_execute_endpoint_marks_executed(db, client):
    _, ws = await _make_auth(db, client)
    create_resp = await client.post(
        f"/api/workspaces/{ws.id}/decisions",
        json={"code": "D01", "title": "Quitar fictício"},
    )
    decision_id = create_resp.json()["id"]

    exec_resp = await client.post(
        f"/api/workspaces/{ws.id}/decisions/{decision_id}/execute",
        json={"note": "ok"},
    )
    assert exec_resp.status_code == 200
    body = exec_resp.json()
    assert body["status"] == "Executado"
    assert body["executed_at"] is not None


@pytest.mark.asyncio
async def test_execute_twice_returns_422(db, client):
    _, ws = await _make_auth(db, client)
    create_resp = await client.post(
        f"/api/workspaces/{ws.id}/decisions",
        json={"code": "D01", "title": "t"},
    )
    decision_id = create_resp.json()["id"]
    await client.post(f"/api/workspaces/{ws.id}/decisions/{decision_id}/execute", json={})
    resp2 = await client.post(f"/api/workspaces/{ws.id}/decisions/{decision_id}/execute", json={})
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_supersede_chain_updates_status(db, client):
    _, ws = await _make_auth(db, client)
    base = f"/api/workspaces/{ws.id}/decisions"
    old = (await client.post(base, json={"code": "D06", "title": "Antigo"})).json()
    new = (await client.post(base, json={"code": "D15", "title": "Novo"})).json()

    sup = await client.post(
        f"{base}/{old['id']}/supersede",
        json={"superseded_by_id": new["id"], "note": "TRS 5"},
    )
    assert sup.status_code == 200
    assert sup.json()["status"] == "Superseded"

    new_get = await client.get(f"{base}/{new['id']}")
    assert new_get.json()["supersedes_id"] == old["id"]


@pytest.mark.asyncio
async def test_cross_tenant_returns_403_or_404(db, client):
    """Workspace stranger tenta acessar Decision de outro WS."""
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"
    create_resp = await client.post(
        f"/api/workspaces/{ws_a.id}/decisions",
        json={"code": "D01", "title": "t"},
    )
    decision_id = create_resp.json()["id"]

    # User B tenta acessar via path do WS A — get_current_workspace
    # filtra por membership; sem membership, 403 ou 404.
    token_b = create_access_token(user_b.id)
    client.headers["Authorization"] = f"Bearer {token_b}"
    resp = await client.get(f"/api/workspaces/{ws_a.id}/decisions/{decision_id}")
    assert resp.status_code in {403, 404}
