"""``GET /members/{id}/cpf[/full]`` — UX decrypt de CPF (ADR-259 §4).

Mascarado é visível a qualquer role do workspace; "ver completo" é
owner-only, gera exatamente 1 row de auditoria sem PII no `details`, e
respeita rate limit. Cross-tenant e ausência de CPF retornam 404.
"""

from __future__ import annotations

import fakeredis
import pytest
from sqlalchemy import func, select

from backend.app.core.security import create_access_token
from backend.app.models.audit_log import AuditLog
from backend.app.models.workspace import Workspace
from backend.app.services.vault import get_vault
from backend.tests import factories

# Placeholder LGPD-safe (allowlist de tests/utils/lint_no_real_pii.py).
_CPF_DIGITS = "12345678909"
_CPF_MASKED = "***.***.789-09"


async def _workspace_with_cpf_member(db, *, role: str = "titular") -> tuple[str, str, str]:
    """IDs capturados como string antes de qualquer commit/rollback adicional
    — objetos ORM expiram após `commit()` e acesso posterior a atributo
    expirado fora do greenlet async explode com `MissingGreenlet`."""
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    vault = get_vault()
    member = await factories.make_member(
        db, workspace=ws, cpf_encrypted=vault.encrypt(_CPF_DIGITS), role=role
    )
    owner_id, ws_id, member_id = owner.id, ws.id, member.id
    await db.commit()
    return owner_id, ws_id, member_id


async def _count_audit(db, action: str) -> int:
    await db.rollback()
    stmt = select(func.count()).select_from(AuditLog).where(AuditLog.action == action)
    return (await db.execute(stmt)).scalar_one()


async def _latest_audit_row(db, action: str) -> AuditLog | None:
    await db.rollback()
    stmt = select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.created_at.desc())
    return (await db.execute(stmt)).scalars().first()


# --- masked: qualquer role -----------------------------------------------


@pytest.mark.asyncio
async def test_owner_sees_masked_cpf(db, client):
    owner_id, ws_id, member_id = await _workspace_with_cpf_member(db)
    client.headers["Authorization"] = f"Bearer {create_access_token(owner_id)}"
    resp = await client.get(f"/api/workspaces/{ws_id}/config/members/{member_id}/cpf")
    assert resp.status_code == 200
    assert resp.json() == {"cpf_masked": _CPF_MASKED}


@pytest.mark.asyncio
async def test_viewer_sees_masked_cpf(db, client):
    owner_id, ws_id, member_id = await _workspace_with_cpf_member(db)
    ws = await db.get(Workspace, ws_id)
    viewer = await factories.make_user(db, email="viewer@test.com")
    await factories.make_workspace_member(db, workspace=ws, user=viewer, role="viewer")
    viewer_id = viewer.id
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(viewer_id)}"
    resp = await client.get(f"/api/workspaces/{ws_id}/config/members/{member_id}/cpf")
    assert resp.status_code == 200
    assert resp.json()["cpf_masked"] == _CPF_MASKED


@pytest.mark.asyncio
async def test_masked_cpf_404_when_member_has_no_cpf(db, client):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    member = await factories.make_member(db, workspace=ws, cpf_encrypted=None)
    owner_id, ws_id, member_id = owner.id, ws.id, member.id
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(owner_id)}"
    resp = await client.get(f"/api/workspaces/{ws_id}/config/members/{member_id}/cpf")
    assert resp.status_code == 404


# --- full: owner-only + auditoria -----------------------------------------


@pytest.mark.asyncio
async def test_owner_reveals_full_cpf_and_audits(db, client):
    owner_id, ws_id, member_id = await _workspace_with_cpf_member(db)
    before = await _count_audit(db, "cpf.view_full")
    client.headers["Authorization"] = f"Bearer {create_access_token(owner_id)}"
    resp = await client.get(f"/api/workspaces/{ws_id}/config/members/{member_id}/cpf/full")
    assert resp.status_code == 200
    assert resp.json() == {"cpf_full": _CPF_DIGITS}
    after = await _count_audit(db, "cpf.view_full")
    assert after == before + 1

    row = await _latest_audit_row(db, "cpf.view_full")
    assert row is not None
    assert row.workspace_id == ws_id
    assert row.actor_user_id == owner_id
    assert row.resource_id == member_id
    assert "12345678909" not in str(row.details)
    assert "123.456.789-09" not in str(row.details)


@pytest.mark.asyncio
async def test_member_cannot_reveal_full_cpf(db, client):
    owner_id, ws_id, member_id = await _workspace_with_cpf_member(db)
    ws = await db.get(Workspace, ws_id)
    mem = await factories.make_user(db, email="mem@test.com")
    await factories.make_workspace_member(db, workspace=ws, user=mem, role="member")
    mem_id = mem.id
    await db.commit()
    before = await _count_audit(db, "cpf.view_full")
    client.headers["Authorization"] = f"Bearer {create_access_token(mem_id)}"
    resp = await client.get(f"/api/workspaces/{ws_id}/config/members/{member_id}/cpf/full")
    assert resp.status_code == 403
    after = await _count_audit(db, "cpf.view_full")
    assert after == before  # role check bloqueia antes do audit dependency


@pytest.mark.asyncio
async def test_viewer_cannot_reveal_full_cpf(db, client):
    owner_id, ws_id, member_id = await _workspace_with_cpf_member(db)
    ws = await db.get(Workspace, ws_id)
    viewer = await factories.make_user(db, email="viewer@test.com")
    await factories.make_workspace_member(db, workspace=ws, user=viewer, role="viewer")
    viewer_id = viewer.id
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(viewer_id)}"
    resp = await client.get(f"/api/workspaces/{ws_id}/config/members/{member_id}/cpf/full")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_full_cpf_404_when_member_has_no_cpf(db, client):
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    member = await factories.make_member(db, workspace=ws, cpf_encrypted=None)
    owner_id, ws_id, member_id = owner.id, ws.id, member.id
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(owner_id)}"
    resp = await client.get(f"/api/workspaces/{ws_id}/config/members/{member_id}/cpf/full")
    assert resp.status_code == 404


# --- cross-tenant ----------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_masked_cpf_404(db, client):
    _owner_a, _ws_a, member_a_id = await _workspace_with_cpf_member(db)
    owner_b = await factories.make_user(db, email="owner-b@test.com")
    ws_b = await factories.make_workspace(db, owner=owner_b)
    owner_b_id, ws_b_id = owner_b.id, ws_b.id
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(owner_b_id)}"
    resp = await client.get(f"/api/workspaces/{ws_b_id}/config/members/{member_a_id}/cpf")
    # workspace de owner_b existe e ele é membro dela — passa a tenancy gate,
    # mas member_a não pertence a ws_b → 404 no lookup do agregado.
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_full_cpf_404(db, client):
    _owner_a, _ws_a, member_a_id = await _workspace_with_cpf_member(db)
    owner_b = await factories.make_user(db, email="owner-b2@test.com")
    ws_b = await factories.make_workspace(db, owner=owner_b)
    owner_b_id, ws_b_id = owner_b.id, ws_b.id
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(owner_b_id)}"
    resp = await client.get(f"/api/workspaces/{ws_b_id}/config/members/{member_a_id}/cpf/full")
    assert resp.status_code == 404


# --- rate limit --------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_cpf_rate_limited(db, client, monkeypatch):
    from backend.app.services import rate_limit as rl

    owner_id, ws_id, member_id = await _workspace_with_cpf_member(db)
    client.headers["Authorization"] = f"Bearer {create_access_token(owner_id)}"
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_get_redis_safe", lambda: fake)
    monkeypatch.setitem(
        rl._DEFAULT_POLICIES,
        "cpf_view_full",
        rl.RateLimitPolicy("cpf_view_full", limit=1, window_s=60),
    )

    url = f"/api/workspaces/{ws_id}/config/members/{member_id}/cpf/full"
    first = await client.get(url)
    assert first.status_code == 200
    second = await client.get(url)
    assert second.status_code == 429
    assert "Retry-After" in second.headers
