"""RBAC de escrita em `/config/members[/accounts]` — `viewer` era ausente
(gap pré-ADR-259 §4 follow-up): endpoints de create/update/delete não
tinham `require_write_role`, então `viewer` conseguia mutar o agregado
`FamilyMember` mesmo sendo role read-only por design (ADR-072)."""

from __future__ import annotations

import pytest

from backend.app.core.security import create_access_token
from backend.tests import factories

MEMBER_PAYLOAD = {
    "full_name": "Novo Membro",
    "short_name": "Novo",
    "role": "filho",
}


async def _setup(db, role: str):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    actor = await factories.make_user(db, email=f"{role}@test.com")
    await factories.make_workspace_member(db, workspace=ws, user=actor, role=role)
    member = await factories.make_member(db, workspace=ws)
    account = await factories.make_bank_account(db, member=member)
    ws_id, member_id, account_id, actor_id = ws.id, member.id, account.id, actor.id
    await db.commit()
    return ws_id, member_id, account_id, actor_id


def _auth(client, actor_id: str):
    client.headers["Authorization"] = f"Bearer {create_access_token(actor_id)}"


@pytest.mark.asyncio
async def test_viewer_cannot_create_member(db, client):
    ws_id, _member_id, _account_id, viewer_id = await _setup(db, "viewer")
    _auth(client, viewer_id)
    resp = await client.post(f"/api/workspaces/{ws_id}/config/members", json=MEMBER_PAYLOAD)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_update_member(db, client):
    ws_id, member_id, _account_id, viewer_id = await _setup(db, "viewer")
    _auth(client, viewer_id)
    resp = await client.put(
        f"/api/workspaces/{ws_id}/config/members/{member_id}", json={"short_name": "X"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_member(db, client):
    ws_id, member_id, _account_id, viewer_id = await _setup(db, "viewer")
    _auth(client, viewer_id)
    resp = await client.delete(f"/api/workspaces/{ws_id}/config/members/{member_id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_account(db, client):
    ws_id, member_id, _account_id, viewer_id = await _setup(db, "viewer")
    _auth(client, viewer_id)
    resp = await client.post(
        f"/api/workspaces/{ws_id}/config/members/{member_id}/accounts",
        json={"institution_code": "c6bank", "account_type": "corrente"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_update_account(db, client):
    ws_id, member_id, account_id, viewer_id = await _setup(db, "viewer")
    _auth(client, viewer_id)
    resp = await client.put(
        f"/api/workspaces/{ws_id}/config/members/{member_id}/accounts/{account_id}",
        json={"institution_code": "c6bank", "account_type": "poupanca"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_account(db, client):
    ws_id, member_id, account_id, viewer_id = await _setup(db, "viewer")
    _auth(client, viewer_id)
    resp = await client.delete(
        f"/api/workspaces/{ws_id}/config/members/{member_id}/accounts/{account_id}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_dismiss_irpf_suggestion(db, client):
    ws_id, _member_id, _account_id, viewer_id = await _setup(db, "viewer")
    _auth(client, viewer_id)
    resp = await client.post(
        f"/api/workspaces/{ws_id}/config/members/irpf-dismissals",
        json={"irpf_year": 2024, "institution_code": "c6bank"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_member_can_still_write(db, client):
    """Sanity check do outro lado da matriz — `member` (WRITE_ROLES) não regride."""
    ws_id, member_id, _account_id, member_actor_id = await _setup(db, "member")
    _auth(client, member_actor_id)
    resp = await client.put(
        f"/api/workspaces/{ws_id}/config/members/{member_id}", json={"short_name": "Y"}
    )
    assert resp.status_code == 200
