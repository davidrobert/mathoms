"""PropertyMarketValue endpoints (ADR-227 §D2 · Sprint A15 Onda 4)."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token
from backend.app.models import PropertyIdentity
from backend.tests import factories


async def _auth_and_property(db, client) -> tuple[str, str]:
    """Allowlisted P1 fixture helper. Cria user/workspace/property e retorna (ws_id, property_id)."""
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    p = PropertyIdentity(
        workspace_id=ws.id,
        titular_key="david",
        codigo_rfb="12",
        endereco_canonical="rua x",
        first_seen_year=2024,
        descricao_sample="CASA",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"
    return ws.id, p.id


def _pmv_payload(property_id: str, **overrides: Any) -> dict[str, Any]:
    """Allowlisted P1 fixture helper. Defaults sane para create_pmv."""
    payload: dict[str, Any] = {
        "property_id": property_id,
        "valor_brl": "1200000.00",
        "valuation_date": "2026-05-01",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_post_creates_pmv_with_201(db: AsyncSession, client: AsyncClient):
    ws_id, p_id = await _auth_and_property(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws_id}/property-market-values", json=_pmv_payload(p_id)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["workspace_id"] == ws_id
    assert body["property_id"] == p_id
    assert body["valor_brl"] == "1200000.00"
    assert body["source"] == "user_declared"
    assert body["superseded_by_id"] is None


@pytest.mark.asyncio
async def test_post_duplicate_date_returns_500_or_409(db: AsyncSession, client: AsyncClient):
    """UNIQUE(property_id, valuation_date) — duplicar mesmo dia deve falhar (500 IntegrityError ou 409 mapeado)."""
    ws_id, p_id = await _auth_and_property(db, client)
    first = await client.post(
        f"/api/workspaces/{ws_id}/property-market-values", json=_pmv_payload(p_id)
    )
    assert first.status_code == 201
    dup = await client.post(
        f"/api/workspaces/{ws_id}/property-market-values", json=_pmv_payload(p_id)
    )
    assert dup.status_code in (409, 500)


@pytest.mark.asyncio
async def test_get_pmv_list(db: AsyncSession, client: AsyncClient):
    ws_id, p_id = await _auth_and_property(db, client)
    await client.post(
        f"/api/workspaces/{ws_id}/property-market-values",
        json=_pmv_payload(p_id, valuation_date="2025-01-01"),
    )
    await client.post(
        f"/api/workspaces/{ws_id}/property-market-values",
        json=_pmv_payload(p_id, valor_brl="1300000.00", valuation_date="2026-05-01"),
    )
    resp = await client.get(f"/api/workspaces/{ws_id}/property-market-values")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    # Ordenado DESC por valuation_date.
    assert rows[0]["valuation_date"] == "2026-05-01"
    assert rows[0]["valor_brl"] == "1300000.00"


@pytest.mark.asyncio
async def test_get_pmv_filter_by_property(db: AsyncSession, client: AsyncClient):
    ws_id, p_id = await _auth_and_property(db, client)
    await client.post(f"/api/workspaces/{ws_id}/property-market-values", json=_pmv_payload(p_id))
    resp = await client.get(f"/api/workspaces/{ws_id}/property-market-values?property_id={p_id}")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["property_id"] == p_id


async def _create_two_pmvs(client, ws_id: str, p_id: str) -> tuple[str, str]:
    """Allowlisted P1 fixture helper. Cria 2 PMVs em datas diferentes e retorna (old_id, new_id)."""
    old = (
        await client.post(
            f"/api/workspaces/{ws_id}/property-market-values",
            json=_pmv_payload(p_id, valuation_date="2025-01-01"),
        )
    ).json()
    new = (
        await client.post(
            f"/api/workspaces/{ws_id}/property-market-values",
            json=_pmv_payload(p_id, valor_brl="1300000.00", valuation_date="2026-05-01"),
        )
    ).json()
    return old["id"], new["id"]


@pytest.mark.asyncio
async def test_patch_supersede_marks_old(db: AsyncSession, client: AsyncClient):
    ws_id, p_id = await _auth_and_property(db, client)
    old_id, new_id = await _create_two_pmvs(client, ws_id, p_id)
    resp = await client.patch(
        f"/api/workspaces/{ws_id}/property-market-values/{old_id}/supersede",
        json={"superseded_by_id": new_id},
    )
    assert resp.status_code == 200
    assert resp.json()["superseded_by_id"] == new_id


async def make_second_property(db, ws_id: str) -> PropertyIdentity:
    """Allowlisted P1 fixture helper — cria segunda PropertyIdentity no mesmo workspace."""
    p2 = PropertyIdentity(
        workspace_id=ws_id,
        titular_key="david",
        codigo_rfb="13",
        endereco_canonical="rua y",
        first_seen_year=2024,
        descricao_sample="OUTRO",
    )
    db.add(p2)
    await db.commit()
    await db.refresh(p2)
    return p2


@pytest.mark.asyncio
async def test_patch_supersede_rejects_different_property(db: AsyncSession, client: AsyncClient):
    """superseded_by_id deve ser do mesmo property_id (422)."""
    ws_id, p_id = await _auth_and_property(db, client)
    p2 = await make_second_property(db, ws_id)
    pmv_a = (
        await client.post(
            f"/api/workspaces/{ws_id}/property-market-values", json=_pmv_payload(p_id)
        )
    ).json()
    pmv_b = (
        await client.post(
            f"/api/workspaces/{ws_id}/property-market-values", json=_pmv_payload(p2.id)
        )
    ).json()
    resp = await client.patch(
        f"/api/workspaces/{ws_id}/property-market-values/{pmv_a['id']}/supersede",
        json={"superseded_by_id": pmv_b["id"]},
    )
    assert resp.status_code == 422
