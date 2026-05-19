"""Integration tests dos endpoints POST/DELETE/GET overrides do card Exposição Cambial (ADR-224 PR-C; sticky pattern ADR-215)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_BASE = "/api/workspaces/{ws}/cards/exposicao-cambial/overrides"


@pytest.mark.asyncio
async def test_list_overrides_empty(auth_client: AsyncClient):
    resp = await auth_client.get(_BASE.format(ws=auth_client.ws_id))
    assert resp.status_code == 200
    assert resp.json() == {"workspace_id": auth_client.ws_id, "overrides": []}


@pytest.mark.asyncio
async def test_create_override_201(auth_client: AsyncClient):
    body = {"match_kind": "ticker", "asset_match_key": "IVVB11", "lastro_moeda": "BRL"}
    resp = await auth_client.post(_BASE.format(ws=auth_client.ws_id), json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["match_kind"] == "ticker"
    assert data["asset_match_key"] == "IVVB11"
    assert data["lastro_moeda"] == "BRL"
    assert data["override_source"] == "user_manual"
    assert data["created_by_user_id"] is not None


@pytest.mark.asyncio
async def test_upsert_override_overwrites(auth_client: AsyncClient):
    body = {"match_kind": "ticker", "asset_match_key": "IVVB11", "lastro_moeda": "BRL"}
    await auth_client.post(_BASE.format(ws=auth_client.ws_id), json=body)
    body2 = {"match_kind": "ticker", "asset_match_key": "IVVB11", "lastro_moeda": "EUR"}
    resp = await auth_client.post(_BASE.format(ws=auth_client.ws_id), json=body2)
    assert resp.status_code == 201
    assert resp.json()["lastro_moeda"] == "EUR"
    # Lista deve ter só 1 row (sticky pattern, ADR-215)
    lst = await auth_client.get(_BASE.format(ws=auth_client.ws_id))
    assert len(lst.json()["overrides"]) == 1


@pytest.mark.asyncio
async def test_delete_override_204(auth_client: AsyncClient):
    body = {"match_kind": "ticker", "asset_match_key": "IVVB11", "lastro_moeda": "BRL"}
    await auth_client.post(_BASE.format(ws=auth_client.ws_id), json=body)
    resp = await auth_client.delete(f"{_BASE.format(ws=auth_client.ws_id)}/ticker/IVVB11")
    assert resp.status_code == 204
    # Lista vazia após delete
    lst = await auth_client.get(_BASE.format(ws=auth_client.ws_id))
    assert lst.json()["overrides"] == []


@pytest.mark.asyncio
async def test_delete_idempotent_when_absent(auth_client: AsyncClient):
    # 204 mesmo quando row não existe — idempotente
    resp = await auth_client.delete(f"{_BASE.format(ws=auth_client.ws_id)}/ticker/NONEXIST")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_invalid_lastro_moeda_422(auth_client: AsyncClient):
    body = {"match_kind": "ticker", "asset_match_key": "X", "lastro_moeda": "JPY"}
    resp = await auth_client.post(_BASE.format(ws=auth_client.ws_id), json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_match_kind_422(auth_client: AsyncClient):
    body = {"match_kind": "bogus", "asset_match_key": "X", "lastro_moeda": "USD"}
    resp = await auth_client.post(_BASE.format(ws=auth_client.ws_id), json=body)
    assert resp.status_code == 422
