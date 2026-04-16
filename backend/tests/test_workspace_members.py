"""Testes da API de gestão de membros (F9)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.models.audit_log import AuditLog
from backend.app.models.workspace_member import WorkspaceMember
from backend.tests import factories


async def _owner_and_member(db, client):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    mem_user = await factories.make_user(db, email="mem@test.com")
    mem = await factories.make_workspace_member(
        db, workspace=ws, user=mem_user, role="member"
    )
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(owner.id)}"
    return owner, ws, mem_user, mem


@pytest.mark.asyncio
async def test_list_members_returns_all(db, client):
    owner, ws, mem_user, _ = await _owner_and_member(db, client)
    resp = await client.get(f"/api/workspaces/{ws.id}/members")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    roles = {m["role"] for m in data["members"]}
    assert roles == {"owner", "member"}


@pytest.mark.asyncio
async def test_viewer_can_list_members(db, client):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    viewer = await factories.make_user(db, email="viewer@test.com")
    await factories.make_workspace_member(
        db, workspace=ws, user=viewer, role="viewer"
    )
    await db.commit()

    client.headers["Authorization"] = f"Bearer {create_access_token(viewer.id)}"
    resp = await client.get(f"/api/workspaces/{ws.id}/members")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_member_role(db, client):
    owner, ws, mem_user, _ = await _owner_and_member(db, client)
    resp = await client.patch(
        f"/api/workspaces/{ws.id}/members/{mem_user.id}",
        json={"role": "viewer"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"

    # Confirma persistência via novo GET (bypassa identity-map da sessão
    # de teste, que é uma sessão diferente da usada pelo endpoint).
    list_resp = await client.get(f"/api/workspaces/{ws.id}/members")
    roles_by_user = {m["user_id"]: m["role"] for m in list_resp.json()["members"]}
    assert roles_by_user[mem_user.id] == "viewer"


@pytest.mark.asyncio
async def test_cannot_promote_to_owner(db, client):
    owner, ws, mem_user, _ = await _owner_and_member(db, client)
    resp = await client.patch(
        f"/api/workspaces/{ws.id}/members/{mem_user.id}",
        json={"role": "owner"},
    )
    # Pydantic rejeita (Literal["member","viewer"])
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cannot_change_owner_role(db, client):
    owner, ws, mem_user, _ = await _owner_and_member(db, client)
    resp = await client.patch(
        f"/api/workspaces/{ws.id}/members/{owner.id}",
        json={"role": "viewer"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "is_owner"


@pytest.mark.asyncio
async def test_remove_member(db, client):
    owner, ws, mem_user, _ = await _owner_and_member(db, client)
    resp = await client.delete(
        f"/api/workspaces/{ws.id}/members/{mem_user.id}"
    )
    assert resp.status_code == 204

    # Confirma persistência via GET (mesmo motivo do teste anterior).
    list_resp = await client.get(f"/api/workspaces/{ws.id}/members")
    user_ids = {m["user_id"] for m in list_resp.json()["members"]}
    assert mem_user.id not in user_ids


@pytest.mark.asyncio
async def test_cannot_remove_owner(db, client):
    owner, ws, _, _ = await _owner_and_member(db, client)
    resp = await client.delete(f"/api/workspaces/{ws.id}/members/{owner.id}")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "is_owner"


@pytest.mark.asyncio
async def test_non_owner_cannot_remove_members(db, client):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    member = await factories.make_user(db, email="mem@test.com")
    await factories.make_workspace_member(
        db, workspace=ws, user=member, role="member"
    )
    third = await factories.make_user(db, email="third@test.com")
    await factories.make_workspace_member(
        db, workspace=ws, user=third, role="viewer"
    )
    await db.commit()

    # member (não-owner) tenta remover o viewer
    client.headers["Authorization"] = f"Bearer {create_access_token(member.id)}"
    resp = await client.delete(f"/api/workspaces/{ws.id}/members/{third.id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_removed_member_token_is_invalidated(db, client):
    """F9.2 · forced logout. Após remoção, o JWT que o membro tinha vira
    inválido — próximas chamadas com ele recebem 401."""
    owner, ws, mem_user, _ = await _owner_and_member(db, client)

    # Membro tinha sessão ativa — simulamos criando um token antes da remoção.
    mem_token = create_access_token(mem_user.id, token_version=0)

    # Owner remove o membro.
    rem_resp = await client.delete(f"/api/workspaces/{ws.id}/members/{mem_user.id}")
    assert rem_resp.status_code == 204

    # Membro tenta usar seu token antigo — 401 com código token_revoked.
    client.headers["Authorization"] = f"Bearer {mem_token}"
    resp = await client.get("/api/me/workspaces")
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert isinstance(detail, dict) and detail.get("code") == "token_revoked"


@pytest.mark.asyncio
async def test_member_operations_are_audited(db, client):
    owner, ws, mem_user, _ = await _owner_and_member(db, client)
    await client.patch(
        f"/api/workspaces/{ws.id}/members/{mem_user.id}",
        json={"role": "viewer"},
    )
    await client.delete(f"/api/workspaces/{ws.id}/members/{mem_user.id}")

    rows = await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == ws.id)
        .order_by(AuditLog.created_at.asc())
    )
    actions = [r.action for r in rows.scalars().all()]
    assert "workspace.member.role_change" in actions
    assert "workspace.member.remove" in actions
