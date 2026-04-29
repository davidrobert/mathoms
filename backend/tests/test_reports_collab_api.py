"""Testes — endpoints legacy de Notes (T6) + Kanban (T3) retornam 410 Gone.

Histórico (ADR-123 · Fase 6.5): testes happy path para
``/workspaces/{ws}/reports/{report_id}/{notes|kanban[/item_id]}``
retornavam 200/201/204.

**Sunset (ADR-154 · M2 · 2026-04-29):** Modo Tático foi removido
(ADR-151), aggregates migraram para Task + WorkspaceNotes (M1).
Endpoints aqui retornam HTTP 410 Gone com payload informativo apontando
para os novos. Estes testes validam o contrato de sunset; suíte
original foi reescrita.
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


def _assert_gone(resp, code: str) -> None:
    assert resp.status_code == 410, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == code
    assert "ADR-154" in detail["message"]
    assert "migrated_to" in detail


@pytest.mark.asyncio
async def test_get_notes_returns_410_gone(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.get(f"/api/workspaces/{ws.id}/reports/{r.id}/notes")
    _assert_gone(resp, "report_notes_gone")


@pytest.mark.asyncio
async def test_put_notes_returns_410_gone(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.put(
        f"/api/workspaces/{ws.id}/reports/{r.id}/notes",
        json={"content": "ignored"},
    )
    _assert_gone(resp, "report_notes_gone")


@pytest.mark.asyncio
async def test_get_kanban_returns_410_gone(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.get(f"/api/workspaces/{ws.id}/reports/{r.id}/kanban")
    _assert_gone(resp, "report_kanban_gone")


@pytest.mark.asyncio
async def test_post_kanban_returns_410_gone(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban",
        json={"titulo": "ignored"},
    )
    _assert_gone(resp, "report_kanban_gone")


@pytest.mark.asyncio
async def test_patch_kanban_item_returns_410_gone(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.patch(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban/item-id",
        json={"titulo": "ignored"},
    )
    _assert_gone(resp, "report_kanban_gone")


@pytest.mark.asyncio
async def test_delete_kanban_item_returns_410_gone(db, client):
    _, ws, r = await _auth(db, client)
    resp = await client.delete(
        f"/api/workspaces/{ws.id}/reports/{r.id}/kanban/item-id",
    )
    _assert_gone(resp, "report_kanban_gone")
