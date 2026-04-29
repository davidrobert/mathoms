"""Integration tests da API de WorkspaceNotes (ADR-153) — CRUD + cross-tenant guard."""

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
async def test_create_note_returns_201(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/notes",
        json={"title": "Agenda", "content": "lembrar de transferir 500", "pinned": True},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Agenda"
    assert body["content"] == "lembrar de transferir 500"
    assert body["pinned"] is True
    assert body["workspace_id"] == ws.id


@pytest.mark.asyncio
async def test_create_note_defaults(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(f"/api/workspaces/{ws.id}/notes", json={})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] is None
    assert body["content"] == ""
    assert body["pinned"] is False


@pytest.mark.asyncio
async def test_list_notes_orders_pinned_first(db, client):
    _, ws = await _make_auth(db, client)
    base = f"/api/workspaces/{ws.id}/notes"

    n1 = (await client.post(base, json={"title": "primeira", "pinned": False})).json()
    n2 = (await client.post(base, json={"title": "segunda", "pinned": True})).json()
    n3 = (await client.post(base, json={"title": "terceira", "pinned": False})).json()

    resp = await client.get(base)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    titles = [n["title"] for n in body["notes"]]
    # Pinned (n2) deve vir antes; entre não-pinned, ordem por updated_at desc.
    assert titles[0] == "segunda"
    assert {titles[1], titles[2]} == {"primeira", "terceira"}


@pytest.mark.asyncio
async def test_patch_updates_partial(db, client):
    _, ws = await _make_auth(db, client)
    create = await client.post(
        f"/api/workspaces/{ws.id}/notes",
        json={"title": "antigo", "content": "x"},
    )
    note_id = create.json()["id"]

    patch = await client.patch(
        f"/api/workspaces/{ws.id}/notes/{note_id}",
        json={"content": "novo conteudo"},
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["content"] == "novo conteudo"
    assert body["title"] == "antigo"


@pytest.mark.asyncio
async def test_patch_unknown_returns_404(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.patch(
        f"/api/workspaces/{ws.id}/notes/00000000-0000-0000-0000-000000000000",
        json={"content": "x"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_pinned_toggle(db, client):
    _, ws = await _make_auth(db, client)
    create = await client.post(f"/api/workspaces/{ws.id}/notes", json={"pinned": False})
    note_id = create.json()["id"]
    resp = await client.patch(f"/api/workspaces/{ws.id}/notes/{note_id}", json={"pinned": True})
    assert resp.status_code == 200
    assert resp.json()["pinned"] is True


@pytest.mark.asyncio
async def test_delete_note_returns_204(db, client):
    _, ws = await _make_auth(db, client)
    create = await client.post(f"/api/workspaces/{ws.id}/notes", json={"title": "x"})
    note_id = create.json()["id"]

    delete = await client.delete(f"/api/workspaces/{ws.id}/notes/{note_id}")
    assert delete.status_code == 204
    delete2 = await client.delete(f"/api/workspaces/{ws.id}/notes/{note_id}")
    assert delete2.status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_returns_403_or_404(db, client):
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    await factories.make_workspace(db, owner=user_b)
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(user_a.id)}"
    note_id = (await client.post(f"/api/workspaces/{ws_a.id}/notes", json={"title": "x"})).json()[
        "id"
    ]
    client.headers["Authorization"] = f"Bearer {create_access_token(user_b.id)}"
    assert (await client.get(f"/api/workspaces/{ws_a.id}/notes")).status_code in {403, 404}
    patch = await client.patch(f"/api/workspaces/{ws_a.id}/notes/{note_id}", json={"content": "x"})
    assert patch.status_code in {403, 404}
