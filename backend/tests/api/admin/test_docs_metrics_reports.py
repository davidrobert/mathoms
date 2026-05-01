"""Testes das rotas de documents, metrics, reports."""

from __future__ import annotations

import pytest

from backend.app.models.report import Report
from backend.tests.factories import make_document, make_user, make_workspace


async def _with_cookie(client, token: str):
    client.cookies.set("ops_session", token, domain="test", path="/admin")


@pytest.mark.asyncio
async def test_purge_preview(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    u = await make_user(db)
    ws = await make_workspace(db, owner=u)
    d1 = await make_document(db, workspace=ws)
    d2 = await make_document(db, workspace=ws)
    await db.commit()

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post(
        "/admin/documents/purge", json={"workspace_id": ws.id, "preview": True}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["preview"] is True and body["count"] == 2 and body["blobs_removed"] is None
    assert set(body["ids"]) == {d1.id, d2.id}
    items = {(it["id"], it["name"]) for it in body["items"]}
    assert items == {(d1.id, d1.original_name), (d2.id, d2.original_name)}


@pytest.mark.asyncio
async def test_purge_requires_scope(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client
) -> None:
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post("/admin/documents/purge", json={"preview": True})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_document_not_found(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client
) -> None:
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.delete("/admin/documents/ghost-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_metrics(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    u = await make_user(db)
    await make_workspace(db, owner=u)
    await db.commit()

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["users_total"] >= 1
    assert body["workspaces_total"] >= 1
    assert body["period_days"] == 30


@pytest.mark.asyncio
async def test_audit_endpoint(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, audit_path, client
) -> None:
    # Login já grava 1 audit. Checar que a rota devolve a entrada.
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/audit")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    assert any(e["action"] == "ops.login" for e in entries)


@pytest.mark.asyncio
async def test_reports_by_workspace(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    u = await make_user(db)
    ws = await make_workspace(db, owner=u)
    db.add(Report(workspace_id=ws.id, title="T1"))
    await db.commit()

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get(f"/admin/reports?workspace_id={ws.id}")
    assert resp.status_code == 200
    titles = [r["title"] for r in resp.json()["reports"]]
    assert titles == ["T1"]


@pytest.mark.asyncio
async def test_reports_purge_preview(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    u = await make_user(db)
    ws = await make_workspace(db, owner=u, name="Familia X")
    db.add(Report(workspace_id=ws.id, title="R1"))
    db.add(Report(workspace_id=ws.id, title="R2"))
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post("/admin/reports/purge", json={"workspace_id": ws.id, "preview": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["preview"] is True and body["count"] == 2 and body["artifacts_to_remove"] == 0
    assert body["scope_context"] == {"owner_email": u.email, "workspace_names": ["Familia X"]}


@pytest.mark.asyncio
async def test_reports_purge_requires_scope(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client
) -> None:
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post("/admin/reports/purge", json={"preview": True})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reports_purge_executes(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    u = await make_user(db)
    ws = await make_workspace(db, owner=u)
    db.add(Report(workspace_id=ws.id, title="R1"))
    await db.commit()

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post(
        "/admin/reports/purge",
        json={"workspace_id": ws.id, "preview": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["preview"] is False
    assert body["count"] == 1

    resp_list = await client.get(f"/admin/reports?workspace_id={ws.id}")
    assert resp_list.json()["reports"] == []
