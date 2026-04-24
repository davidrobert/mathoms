"""Testes de integração — Notes (T6) + Kanban (T3) do relatório premium.

ADR-123 · Fase 6.5.
"""

from __future__ import annotations

import pytest

from backend.app.core.security import create_access_token
from backend.tests import factories


async def _auth(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    report = await factories.make_report(db, workspace=ws)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user, ws, report


# ─── Notes ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_notes_empty_returns_null(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.get(f"/api/workspaces/{ws.id}/reports/{r.id}/notes")
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_put_notes_creates_then_updates(db, client):
    _, ws, r = await _auth(db, client)
    # Cria
    resp = await client.put(
        f"/api/workspaces/{ws.id}/reports/{r.id}/notes",
        json={"content": "Primeiro texto"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "Primeiro texto"
    note_id = body["id"]

    # Atualiza (idempotente — mesmo id)
    resp = await client.put(
        f"/api/workspaces/{ws.id}/reports/{r.id}/notes",
        json={"content": "Revisado"},
    )
    assert resp.status_code == 200
    body2 = resp.json()
    assert body2["id"] == note_id
    assert body2["content"] == "Revisado"


@pytest.mark.asyncio
async def test_get_notes_returns_after_put(db, client):
    _, ws, r = await _auth(db, client)
    await client.put(
        f"/api/workspaces/{ws.id}/reports/{r.id}/notes",
        json={"content": "persistido"},
    )
    resp = await client.get(f"/api/workspaces/{ws.id}/reports/{r.id}/notes")
    assert resp.status_code == 200
    assert resp.json()["content"] == "persistido"


@pytest.mark.asyncio
async def test_put_notes_report_wrong_workspace_404(db, client):
    _, ws, _ = await _auth(db, client)
    resp = await client.put(
        f"/api/workspaces/{ws.id}/reports/nonexistent/notes",
        json={"content": "x"},
    )
    assert resp.status_code == 404


# ─── Kanban ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_kanban_list_empty(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.get(f"/api/workspaces/{ws.id}/reports/{r.id}/kanban")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


@pytest.mark.asyncio
async def test_kanban_create_then_list(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban",
        json={"titulo": "Rebalancear", "coluna": "a_fazer", "prioridade": "alta"},
    )
    assert resp.status_code == 201
    item = resp.json()
    assert item["titulo"] == "Rebalancear"
    assert item["coluna"] == "a_fazer"
    assert item["prioridade"] == "alta"

    list_resp = await client.get(f"/api/workspaces/{ws.id}/reports/{r.id}/kanban")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == item["id"]


@pytest.mark.asyncio
async def test_kanban_patch_muda_coluna(db, client):
    _, ws, r = await _auth(db, client)
    r1 = await client.post(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban",
        json={"titulo": "X", "coluna": "a_fazer"},
    )
    item_id = r1.json()["id"]
    resp = await client.patch(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban/{item_id}",
        json={"coluna": "em_andamento"},
    )
    assert resp.status_code == 200
    assert resp.json()["coluna"] == "em_andamento"


@pytest.mark.asyncio
async def test_kanban_delete_returns_204(db, client):
    _, ws, r = await _auth(db, client)
    c = await client.post(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban",
        json={"titulo": "Del me"},
    )
    item_id = c.json()["id"]
    resp = await client.delete(f"/api/workspaces/{ws.id}/reports/{r.id}/kanban/{item_id}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/workspaces/{ws.id}/reports/{r.id}/kanban")
    assert list_resp.json()["items"] == []


@pytest.mark.asyncio
async def test_kanban_patch_nonexistent_404(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.patch(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban/not-a-real-id",
        json={"coluna": "concluido"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_kanban_validation_prioridade_invalida(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban",
        json={"titulo": "X", "prioridade": "urgentissima"},
    )
    assert resp.status_code == 422
