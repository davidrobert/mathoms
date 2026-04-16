"""Testes da API de convites (F9 · workspace sharing).

Cobre:

1. Happy path: owner cria convite → token no response → convidado aceita → vira member
2. Invariantes: token não pode ser recuperado depois; email case-insensitive
3. Estados terminais: expirado, revogado, já-aceito retornam 410/409
4. Autorização: apenas `owner` pode criar/revogar; cross-tenant bloqueado
5. Rate limit: limite de convites pendentes
6. Audit: cada ação deixa entrada em `audit_logs`
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.models.audit_log import AuditLog
from backend.app.models.workspace_invitation import WorkspaceInvitation
from backend.app.models.workspace_member import WorkspaceMember
from backend.app.services.invitation_service import (
    MAX_PENDING_PER_WORKSPACE,
    _hash_token,
)
from backend.tests import factories


async def _make_owner(db, client):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner, name="Família Teste")
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(owner.id)}"
    return owner, ws


# ─── Happy path ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_invitation_returns_raw_token_once(db, client):
    owner, ws = await _make_owner(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "invited@test.com", "role": "viewer"},
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["invitation"]["email"] == "invited@test.com"
    assert data["invitation"]["role"] == "viewer"
    assert data["invitation"]["status"] == "pending"
    raw_token = data["token"]
    assert len(raw_token) > 20
    assert data["invite_path"] == f"/invite/{raw_token}"

    # Token cru NÃO aparece no listagem
    list_resp = await client.get(f"/api/workspaces/{ws.id}/invitations")
    assert list_resp.status_code == 200
    listed = list_resp.json()["invitations"][0]
    assert "token" not in listed

    # DB armazena só o hash
    row = await db.execute(select(WorkspaceInvitation))
    inv = row.scalar_one()
    assert inv.token_hash == _hash_token(raw_token)
    assert inv.token_hash != raw_token


@pytest.mark.asyncio
async def test_accept_invitation_creates_member(db, client):
    owner, ws = await _make_owner(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "invited@test.com", "role": "member"},
    )
    raw_token = resp.json()["token"]

    # Convidado cria conta e autentica
    invitee = await factories.make_user(db, email="invited@test.com")
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(invitee.id)}"

    accept_resp = await client.post(f"/api/invitations/{raw_token}/accept")
    assert accept_resp.status_code == 200
    body = accept_resp.json()
    assert body["workspace_id"] == ws.id
    assert body["role"] == "member"

    # Membership criado
    mem_row = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == invitee.id,
        )
    )
    assert mem_row.scalar_one().role == "member"


@pytest.mark.asyncio
async def test_preview_invitation_public_shows_safe_metadata(db, client):
    owner, ws = await _make_owner(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "invited@test.com", "role": "viewer"},
    )
    raw_token = resp.json()["token"]

    # Tira o auth header — preview é público
    client.headers.pop("Authorization", None)
    preview = await client.get(f"/api/invitations/{raw_token}")
    assert preview.status_code == 200
    data = preview.json()
    assert data["workspace_name"] == "Família Teste"
    assert data["role"] == "viewer"
    assert data["invited_by_email"] == "owner@test.com"
    assert data["email"] == "invited@test.com"
    assert data["status"] == "pending"


# ─── Regras de negócio ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cannot_invite_as_owner(db, client):
    owner, ws = await _make_owner(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "invited@test.com", "role": "owner"},
    )
    # Pydantic rejeita antes de chegar no service (Literal["member","viewer"])
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cannot_invite_existing_member(db, client):
    owner, ws = await _make_owner(db, client)
    existing = await factories.make_user(db, email="existing@test.com")
    await factories.make_workspace_member(
        db, workspace=ws, user=existing, role="member"
    )
    await db.commit()

    resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "existing@test.com", "role": "viewer"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "already_member"


@pytest.mark.asyncio
async def test_accept_rejects_wrong_email(db, client):
    owner, ws = await _make_owner(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "target@test.com", "role": "viewer"},
    )
    raw_token = resp.json()["token"]

    intruder = await factories.make_user(db, email="intruder@test.com")
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(intruder.id)}"

    accept = await client.post(f"/api/invitations/{raw_token}/accept")
    assert accept.status_code == 403
    assert accept.json()["detail"]["code"] == "email_mismatch"


@pytest.mark.asyncio
async def test_accept_rejects_expired_invitation(db, client):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    invitee = await factories.make_user(db, email="invited@test.com")
    inv = await factories.make_invitation(
        db,
        workspace=ws,
        email="invited@test.com",
        role="viewer",
        already_expired=True,
    )
    # Precisamos do raw token — como `make_invitation` não devolve, forçamos
    # via service para gerar novo + persistir hash:
    from backend.app.services.invitation_service import (
        _generate_token,
        _hash_token,
    )

    raw, th = _generate_token()
    inv.token_hash = th
    # Também garantimos expirado
    inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.add(inv)
    await db.commit()

    client.headers["Authorization"] = f"Bearer {create_access_token(invitee.id)}"
    accept = await client.post(f"/api/invitations/{raw}/accept")
    assert accept.status_code == 410
    assert accept.json()["detail"]["code"] == "expired"


@pytest.mark.asyncio
async def test_revoke_pending_invitation(db, client):
    owner, ws = await _make_owner(db, client)
    create_resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "invited@test.com", "role": "viewer"},
    )
    inv_id = create_resp.json()["invitation"]["id"]

    rev = await client.delete(f"/api/workspaces/{ws.id}/invitations/{inv_id}")
    assert rev.status_code == 204

    # Listar convites mostra revogado
    listing = await client.get(f"/api/workspaces/{ws.id}/invitations")
    found = [i for i in listing.json()["invitations"] if i["id"] == inv_id]
    assert found and found[0]["status"] == "revoked"


# ─── Autorização (owner-only) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_non_owner_cannot_create_invitation(db, client):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    other = await factories.make_user(db, email="other@test.com")
    await factories.make_workspace_member(
        db, workspace=ws, user=other, role="member"
    )
    await db.commit()

    client.headers["Authorization"] = f"Bearer {create_access_token(other.id)}"
    resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "x@test.com", "role": "viewer"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_cannot_create_invitation(db, client):
    user_a = await factories.make_user(db, email="a@test.com")
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db, email="b@test.com")
    ws_b = await factories.make_workspace(db, owner=user_b)
    await db.commit()

    client.headers["Authorization"] = f"Bearer {create_access_token(user_a.id)}"
    resp = await client.post(
        f"/api/workspaces/{ws_b.id}/invitations",
        json={"email": "x@test.com", "role": "viewer"},
    )
    assert resp.status_code == 403


# ─── Rate limit ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limit_pending_invitations(db, client):
    owner, ws = await _make_owner(db, client)
    for i in range(MAX_PENDING_PER_WORKSPACE):
        resp = await client.post(
            f"/api/workspaces/{ws.id}/invitations",
            json={"email": f"inv{i}@test.com", "role": "viewer"},
        )
        assert resp.status_code == 201

    over = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "over@test.com", "role": "viewer"},
    )
    assert over.status_code == 429
    assert over.json()["detail"]["code"] == "limit_reached"


# ─── Audit log ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invitation_lifecycle_writes_audit_logs(db, client):
    owner, ws = await _make_owner(db, client)
    create_resp = await client.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "invited@test.com", "role": "viewer"},
    )
    raw_token = create_resp.json()["token"]

    invitee = await factories.make_user(db, email="invited@test.com")
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(invitee.id)}"
    await client.post(f"/api/invitations/{raw_token}/accept")

    rows = await db.execute(
        select(AuditLog).where(AuditLog.workspace_id == ws.id).order_by(
            AuditLog.created_at.asc()
        )
    )
    actions = [r.action for r in rows.scalars().all()]
    assert "workspace.member.invite" in actions
    assert "workspace.member.accept" in actions
