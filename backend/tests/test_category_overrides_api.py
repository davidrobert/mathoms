"""Override CRUD endpoints (A7.3 · ADR-137)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token
from backend.app.models.category_template import CategoryTemplate
from backend.tests import factories


async def _seed_template(db: AsyncSession) -> None:
    rows = [
        ("moradia", "Moradia", "expense", ["ALUGUEL", "IPTU"], 1),
        ("alimentacao", "Alimentação", "expense", ["MERCADO"], 2),
        ("receita_pj", "Receita PJ", "income", ["NOTA FISCAL"], 3),
    ]
    for key, label, ctype, kw, order in rows:
        db.add(
            CategoryTemplate(
                id=str(uuid.uuid4()),
                template_version=1,
                key=key,
                label=label,
                category_type=ctype,
                default_keywords=kw,
                sort_order=order,
                metadata_json={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
    await db.commit()


async def _auth(db, client) -> tuple[str, str]:
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user.id, ws.id


@pytest.fixture(autouse=True)
def _no_redis(monkeypatch):
    from backend.app.services import category_cache

    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: None)


@pytest.mark.asyncio
async def test_list_resolved_returns_template_when_no_overrides(
    db: AsyncSession, client: AsyncClient
):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    resp = await client.get(f"/api/workspaces/{ws_id}/config/category-overrides/resolved")
    assert resp.status_code == 200
    codes = {c["code"] for c in resp.json()["categories"]}
    assert "moradia" in codes
    assert "alimentacao" in codes


@pytest.mark.asyncio
async def test_list_resolved_returns_empty_when_no_template(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    resp = await client.get(f"/api/workspaces/{ws_id}/config/category-overrides/resolved")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_resolved_includes_template_version_fields(
    db: AsyncSession, client: AsyncClient
):
    """ADR-185 §4: DTO carrega ``template_version_used`` + ``latest_template_version``."""
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    resp = await client.get(f"/api/workspaces/{ws_id}/config/category-overrides/resolved")
    assert resp.status_code == 200
    payload = resp.json()
    # ``ACTIVE_TEMPLATE_VERSION = 1``; seed só tem v1 → ambos iguais.
    assert payload["template_version_used"] == 1
    assert payload["latest_template_version"] == 1


async def _seed_v2_row(db: AsyncSession) -> None:
    """Adiciona 1 row em ``category_templates`` com ``template_version=2`` (sem cobrir v1)."""
    db.add(
        CategoryTemplate(
            id=str(uuid.uuid4()),
            template_version=2,
            key="moradia",
            label="Moradia (v2)",
            category_type="expense",
            default_keywords=["ALUGUEL"],
            sort_order=1,
            metadata_json={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_list_resolved_signals_outdated_when_v2_seeded(db: AsyncSession, client: AsyncClient):
    """v2 seedada com workspace em v1 ⇒ ``used < latest`` (UI mostra sinal sem CTA)."""
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    await _seed_v2_row(db)
    resp = await client.get(f"/api/workspaces/{ws_id}/config/category-overrides/resolved")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["template_version_used"] == 1
    assert payload["latest_template_version"] == 2


@pytest.mark.asyncio
async def test_upsert_creates_override_with_keywords(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    resp = await client.put(
        f"/api/workspaces/{ws_id}/config/category-overrides/moradia",
        json={"keywords": ["NOVA_KW"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "moradia"
    assert data["keywords"] == ["NOVA_KW"]
    assert data["id"] is not None  # override id


@pytest.mark.asyncio
async def test_upsert_with_label_change(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    resp = await client.put(
        f"/api/workspaces/{ws_id}/config/category-overrides/moradia",
        json={"name": "Casa Renomeada"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Casa Renomeada"


@pytest.mark.asyncio
async def test_upsert_unknown_template_key_returns_404(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    resp = await client.put(
        f"/api/workspaces/{ws_id}/config/category-overrides/naoexiste",
        json={"name": "X"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upsert_idempotent(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    first = await client.put(
        f"/api/workspaces/{ws_id}/config/category-overrides/moradia",
        json={"keywords": ["A"]},
    )
    second = await client.put(
        f"/api/workspaces/{ws_id}/config/category-overrides/moradia",
        json={"keywords": ["B"]},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["keywords"] == ["B"]


@pytest.mark.asyncio
async def test_upsert_with_monthly_cap(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    resp = await client.put(
        f"/api/workspaces/{ws_id}/config/category-overrides/alimentacao",
        json={"monthly_cap": 3000.50},
    )
    assert resp.status_code == 200
    assert resp.json()["monthly_cap"] == pytest.approx(3000.50)


@pytest.mark.asyncio
async def test_disable_filters_from_resolved_list(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    resp = await client.delete(f"/api/workspaces/{ws_id}/config/category-overrides/moradia")
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"

    listing = await client.get(f"/api/workspaces/{ws_id}/config/category-overrides/resolved")
    codes = {c["code"] for c in listing.json()["categories"]}
    assert "moradia" not in codes
    assert "alimentacao" in codes


@pytest.mark.asyncio
async def test_reset_removes_override(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    await client.put(
        f"/api/workspaces/{ws_id}/config/category-overrides/moradia",
        json={"name": "Custom"},
    )
    resp = await client.post(f"/api/workspaces/{ws_id}/config/category-overrides/moradia/reset")
    assert resp.status_code == 200
    assert resp.json()["status"] == "reset"

    listing = await client.get(f"/api/workspaces/{ws_id}/config/category-overrides/resolved")
    moradia = next(c for c in listing.json()["categories"] if c["code"] == "moradia")
    assert moradia["name"] == "Moradia"


@pytest.mark.asyncio
async def test_reset_with_no_existing_override_is_noop(db: AsyncSession, client: AsyncClient):
    _, ws_id = await _auth(db, client)
    await _seed_template(db)
    resp = await client.post(f"/api/workspaces/{ws_id}/config/category-overrides/moradia/reset")
    assert resp.status_code == 200
