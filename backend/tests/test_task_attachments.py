"""Testes de TaskAttachment (ADR-074 §F8.3).

Cobre:
- Upload + metadata persistido
- List escopo por task + workspace
- Download com tenancy check
- Delete remove row e arquivo
- Multi-tenant isolation
- Validação extensão / tamanho
"""

from __future__ import annotations

import io

import pytest

from backend.app.core.security import create_access_token
from backend.app.services.storage import StorageService
from backend.tests import factories


async def _make_auth_ws(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user, ws


async def _make_task_in_ws(db, client, ws, title="Task de teste"):
    r = await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={"title": title, "category": "Invest", "priority": "R"},
    )
    assert r.status_code == 201
    return r.json()


# ─── Upload + List ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_attachment_returns_201(db, client, tmp_path, monkeypatch):
    """Upload de PDF válido. Usa tmp_path como STORAGE_ROOT para isolamento."""
    monkeypatch.setattr(
        "backend.app.core.config.settings.STORAGE_ROOT",
        str(tmp_path),
    )

    _, ws = await _make_auth_ws(db, client)
    task = await _make_task_in_ws(db, client, ws)

    file_content = b"%PDF-1.4\n%fake content for testing"
    files = {"file": ("comprovante.pdf", io.BytesIO(file_content), "application/pdf")}
    resp = await client.post(
        f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments",
        files=files,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["original_filename"] == "comprovante.pdf"
    assert data["size_bytes"] == len(file_content)
    assert data["content_type"] == "application/pdf"
    assert data["task_id"] == task["id"]


@pytest.mark.asyncio
async def test_list_attachments_returns_uploaded(db, client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.core.config.settings.STORAGE_ROOT",
        str(tmp_path),
    )
    _, ws = await _make_auth_ws(db, client)
    task = await _make_task_in_ws(db, client, ws)

    files = {"file": ("nota.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")}
    await client.post(f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments", files=files)

    resp = await client.get(f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["attachments"][0]["original_filename"] == "nota.pdf"


@pytest.mark.asyncio
async def test_upload_rejects_disallowed_extension(db, client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.core.config.settings.STORAGE_ROOT",
        str(tmp_path),
    )
    _, ws = await _make_auth_ws(db, client)
    task = await _make_task_in_ws(db, client, ws)

    files = {"file": ("malicioso.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")}
    resp = await client.post(f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments", files=files)
    assert resp.status_code == 400
    assert "não permitido" in resp.json()["detail"].lower()


# ─── Download ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_download_returns_file_content(db, client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.core.config.settings.STORAGE_ROOT",
        str(tmp_path),
    )
    _, ws = await _make_auth_ws(db, client)
    task = await _make_task_in_ws(db, client, ws)

    body = b"%PDF-1.4\ntest payload abc"
    files = {"file": ("x.pdf", io.BytesIO(body), "application/pdf")}
    up = await client.post(f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments", files=files)
    att_id = up.json()["id"]

    resp = await client.get(
        f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments/{att_id}/download"
    )
    assert resp.status_code == 200
    assert resp.content == body


# ─── Delete ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_removes_row_and_file(db, client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.core.config.settings.STORAGE_ROOT",
        str(tmp_path),
    )
    _, ws = await _make_auth_ws(db, client)
    task = await _make_task_in_ws(db, client, ws)

    files = {"file": ("x.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}
    up = await client.post(f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments", files=files)
    att_id = up.json()["id"]

    # File existe antes
    storage = StorageService(storage_root=tmp_path)
    att_dir = storage.tenant_root(ws.id) / "task_attachments" / task["id"]
    assert any(att_dir.iterdir())

    # Delete
    resp = await client.delete(f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments/{att_id}")
    assert resp.status_code == 204

    # List retorna vazio
    resp = await client.get(f"/api/workspaces/{ws.id}/tasks/{task['id']}/attachments")
    assert resp.json()["total"] == 0

    # Arquivo removido do disco
    assert not list(att_dir.iterdir())


# ─── Multi-tenant isolation ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_upload_returns_403(db, client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.core.config.settings.STORAGE_ROOT",
        str(tmp_path),
    )
    user_a = await factories.make_user(db)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    task_b = await factories.make_task(db, workspace=ws_b)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"

    files = {"file": ("x.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}
    resp = await client.post(
        f"/api/workspaces/{ws_b.id}/tasks/{task_b.id}/attachments", files=files
    )
    assert resp.status_code == 403
