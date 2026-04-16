"""Tests for PasswordVault CRUD API and VaultService encryption."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vault_list_empty(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/vault/passwords")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["passwords"] == []


@pytest.mark.asyncio
async def test_vault_create_password(auth_client: AsyncClient):
    resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/vault/passwords", json={
        "label": "Banco Itaú PDF",
        "password": "minhasenha123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == "Banco Itaú PDF"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "encrypted_password" not in data


@pytest.mark.asyncio
async def test_vault_list_after_create(auth_client: AsyncClient):
    await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/vault/passwords", json={
        "label": "Senha 1", "password": "pass1",
    })
    await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/vault/passwords", json={
        "label": "Senha 2", "password": "pass2",
    })
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/vault/passwords")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["passwords"]) == 2


@pytest.mark.asyncio
async def test_vault_delete_password(auth_client: AsyncClient):
    resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/vault/passwords", json={
        "label": "Temporária", "password": "temp",
    })
    pw_id = resp.json()["id"]

    del_resp = await auth_client.delete(f"/api/workspaces/{auth_client.ws_id}/vault/passwords/{pw_id}")
    assert del_resp.status_code == 204

    list_resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/vault/passwords")
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_vault_delete_not_found(auth_client: AsyncClient):
    resp = await auth_client.delete(f"/api/workspaces/{auth_client.ws_id}/vault/passwords/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_vault_create_validation_empty_label(auth_client: AsyncClient):
    resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/vault/passwords", json={
        "label": "", "password": "pass",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_vault_create_validation_empty_password(auth_client: AsyncClient):
    resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/vault/passwords", json={
        "label": "Test", "password": "",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_vault_unauthorized(client: AsyncClient):
    resp = await client.get(f"/api/workspaces/00000000-0000-0000-0000-000000000000/vault/passwords")
    assert resp.status_code in (401, 403)
