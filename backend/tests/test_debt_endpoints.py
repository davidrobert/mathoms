"""Debt CRUD endpoints (ADR-227 §D1 · Sprint A15 Onda 4)."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token
from backend.app.models import (
    DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
    DEBT_TIPO_OUTRO,
    PropertyIdentity,
)
from backend.tests import factories


async def _auth(db, client) -> tuple[str, str]:
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user.id, ws.id


def _debt_payload(**overrides: Any) -> dict[str, Any]:
    """Allowlisted P1 fixture helper. Defaults sane para create_debt."""
    payload: dict[str, Any] = {
        "tipo": "outro",
        "descricao": "CDC carro",
        "saldo_devedor_brl": "25000.00",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_post_debt_creates_with_201_and_response_model(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    resp = await client.post(f"/api/workspaces/{ws_id}/debts", json=_debt_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["workspace_id"] == ws_id
    assert body["tipo"] == "outro"
    assert body["saldo_devedor_brl"] == "25000.00"
    assert body["needs_review"] is False
    assert body["source"] == "user_declared"


@pytest.mark.asyncio
async def test_post_debt_with_no_identity_returns_422(db: AsyncSession, client: AsyncClient):
    """CHECK chk_debt_identity espelhado em Pydantic model_validator."""
    _, ws_id = await _auth(db, client)
    bad = _debt_payload(descricao=None)  # sem family_member_id, property_id ou descricao
    resp = await client.post(f"/api/workspaces/{ws_id}/debts", json=bad)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_debts_returns_list(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await client.post(f"/api/workspaces/{ws_id}/debts", json=_debt_payload(descricao="a"))
    await client.post(f"/api/workspaces/{ws_id}/debts", json=_debt_payload(descricao="b"))
    resp = await client.get(f"/api/workspaces/{ws_id}/debts")
    assert resp.status_code == 200
    assert {d["descricao"] for d in resp.json()} == {"a", "b"}


@pytest.mark.asyncio
async def test_get_debts_filter_needs_review(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await client.post(
        f"/api/workspaces/{ws_id}/debts", json=_debt_payload(descricao="needs", needs_review=True)
    )
    await client.post(
        f"/api/workspaces/{ws_id}/debts", json=_debt_payload(descricao="ok", needs_review=False)
    )
    resp = await client.get(f"/api/workspaces/{ws_id}/debts?needs_review=true")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["descricao"] == "needs"


@pytest.mark.asyncio
async def test_patch_debt_updates_field(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    created = (await client.post(f"/api/workspaces/{ws_id}/debts", json=_debt_payload())).json()
    debt_id = created["id"]
    resp = await client.patch(
        f"/api/workspaces/{ws_id}/debts/{debt_id}",
        json={"saldo_devedor_brl": "20000.00", "needs_review": True},
    )
    assert resp.status_code == 200
    assert resp.json()["saldo_devedor_brl"] == "20000.00"
    assert resp.json()["needs_review"] is True


@pytest.mark.asyncio
async def test_delete_debt_returns_204(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    created = (await client.post(f"/api/workspaces/{ws_id}/debts", json=_debt_payload())).json()
    resp = await client.delete(f"/api/workspaces/{ws_id}/debts/{created['id']}")
    assert resp.status_code == 204
    list_resp = await client.get(f"/api/workspaces/{ws_id}/debts")
    assert list_resp.json() == []


async def make_two_users_workspaces(db) -> tuple:
    """Allowlisted P1 fixture helper. Retorna ((user_a, ws_a), (user_b, ws_b))."""
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await db.commit()
    return (user_a, ws_a), (user_b, ws_b)


@pytest.mark.asyncio
async def test_tenancy_isolation_between_workspaces(db: AsyncSession, client: AsyncClient):
    """Workspace A não vê Debts do workspace B."""
    (user_a, ws_a), (user_b, ws_b) = await make_two_users_workspaces(db)
    client.headers["Authorization"] = f"Bearer {create_access_token(user_a.id)}"
    created = (await client.post(f"/api/workspaces/{ws_a.id}/debts", json=_debt_payload())).json()
    client.headers["Authorization"] = f"Bearer {create_access_token(user_b.id)}"
    own_list = await client.get(f"/api/workspaces/{ws_b.id}/debts")
    cross_get = await client.get(f"/api/workspaces/{ws_a.id}/debts")
    cross_patch = await client.patch(
        f"/api/workspaces/{ws_a.id}/debts/{created['id']}", json={"needs_review": True}
    )
    assert own_list.json() == []
    assert cross_get.status_code in (403, 404)
    assert cross_patch.status_code in (403, 404)


async def make_property_in_workspace(db, ws_id: str) -> PropertyIdentity:
    """Allowlisted P1 fixture helper."""
    p = PropertyIdentity(
        workspace_id=ws_id,
        titular_key="david",
        codigo_rfb="12",
        endereco_canonical="rua x",
        first_seen_year=2024,
        descricao_sample="CASA",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_post_debt_with_property_link(db: AsyncSession, client: AsyncClient):
    """POST com property_id válido cria Debt vinculada (cenário Onda 5 batch review)."""
    _, ws_id = await _auth(db, client)
    p = await make_property_in_workspace(db, ws_id)
    payload = _debt_payload(
        property_id=p.id,
        tipo="financiamento_imobiliario",
        saldo_devedor_brl="300000.00",
        percentual_atribuicao_imovel="100.00",
    )
    resp = await client.post(f"/api/workspaces/{ws_id}/debts", json=payload)
    assert resp.status_code == 201
    assert resp.json()["property_id"] == p.id
    assert resp.json()["tipo"] == "financiamento_imobiliario"
