"""Integration: write-through cache invalidation em ``CategoryOverrideService`` (A11.W1)."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.categorization import (
    CategoryOverrideConfig,
    CategoryOverrideService,
)
from backend.app.core.security import create_access_token
from backend.app.models.category_template import CategoryTemplate
from backend.app.services.category_resolver import resolve_categories
from backend.app.services.storage import category_cache
from backend.tests import factories


class _FakeRedis:
    """Stub in-process: get/set/delete/scan_iter via dict — exercita o path completo do cache."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                n += 1
        return n

    def scan_iter(self, match: str):
        if not match.endswith("*"):
            yield from (k for k in list(self._store) if k == match)
            return
        prefix = match[:-1]
        yield from (k for k in list(self._store) if k.startswith(prefix))

    def ping(self) -> bool:
        return True


def _cached_keys(fake: _FakeRedis) -> list[str]:
    return [k for k in fake._store if k.startswith("categories:ws=")]


def _template_row(key: str, label: str, ctype: str, kw: list[str], order: int) -> CategoryTemplate:
    now = datetime.now(timezone.utc)
    return CategoryTemplate(
        id=str(uuid.uuid4()),
        template_version=1,
        key=key,
        label=label,
        category_type=ctype,
        default_keywords=kw,
        sort_order=order,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )


async def _seed_template(db: AsyncSession) -> None:
    db.add(_template_row("moradia", "Moradia", "expense", ["ALUGUEL", "IPTU"], 1))
    db.add(_template_row("alimentacao", "Alimentação", "expense", ["MERCADO"], 2))
    await db.commit()


@pytest_asyncio.fixture
async def seeded_workspace(db: AsyncSession):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    await _seed_template(db)
    return user, ws


@pytest.fixture
def fake_redis(monkeypatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_upsert_invalidates_cache_within_100ms(
    db: AsyncSession, fake_redis: _FakeRedis, seeded_workspace
) -> None:
    _, ws = seeded_workspace
    await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert _cached_keys(fake_redis), "primeira resolução deveria popular o cache"

    t0 = time.monotonic()
    override_id = await CategoryOverrideService(db).upsert(
        CategoryOverrideConfig(
            workspace_id=ws.id, template_key="moradia", label_override="Casa Renomeada"
        )
    )
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    assert override_id and elapsed_ms < 100.0, f"upsert demorou {elapsed_ms:.1f} ms"
    assert _cached_keys(fake_redis) == [], "cache deveria estar vazio pós-invalidate"
    refreshed = await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert next(c.label for c in refreshed if c.key == "moradia") == "Casa Renomeada"


@pytest.mark.asyncio
async def test_disable_invalidates_cache(
    db: AsyncSession, fake_redis: _FakeRedis, seeded_workspace
) -> None:
    _, ws = seeded_workspace
    await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert _cached_keys(fake_redis)

    await CategoryOverrideService(db).disable(ws.id, "moradia")

    assert _cached_keys(fake_redis) == []
    refreshed = await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert all(c.key != "moradia" for c in refreshed)


@pytest.mark.asyncio
async def test_reset_invalidates_cache(
    db: AsyncSession, fake_redis: _FakeRedis, seeded_workspace
) -> None:
    _, ws = seeded_workspace
    service = CategoryOverrideService(db)
    await service.upsert(
        CategoryOverrideConfig(workspace_id=ws.id, template_key="moradia", label_override="Lar")
    )
    primed = await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert next(c.label for c in primed if c.key == "moradia") == "Lar"
    assert _cached_keys(fake_redis)

    await service.reset(ws.id, "moradia")

    assert _cached_keys(fake_redis) == []
    after_reset = await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert next(c.label for c in after_reset if c.key == "moradia") == "Moradia"


async def _prime_two_overrides(db: AsyncSession, ws_id: str) -> CategoryOverrideService:
    service = CategoryOverrideService(db)
    await service.upsert(
        CategoryOverrideConfig(workspace_id=ws_id, template_key="moradia", label_override="Lar")
    )
    await service.upsert(
        CategoryOverrideConfig(
            workspace_id=ws_id, template_key="alimentacao", label_override="Comida"
        )
    )
    return service


@pytest.mark.asyncio
async def test_reset_all_invalidates_cache(
    db: AsyncSession, fake_redis: _FakeRedis, seeded_workspace
) -> None:
    _, ws = seeded_workspace
    service = await _prime_two_overrides(db, ws.id)
    await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert _cached_keys(fake_redis)
    count = await service.reset_all(ws.id)
    assert count == 2
    assert _cached_keys(fake_redis) == []
    after = await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert next(c.label for c in after if c.key == "moradia") == "Moradia"
    assert next(c.label for c in after if c.key == "alimentacao") == "Alimentação"


@pytest.mark.asyncio
async def test_reset_all_no_overrides_is_noop(
    db: AsyncSession, fake_redis: _FakeRedis, seeded_workspace
) -> None:
    _, ws = seeded_workspace
    count = await CategoryOverrideService(db).reset_all(ws.id)
    assert count == 0


@pytest.mark.asyncio
async def test_cache_failure_does_not_abort_write(
    db: AsyncSession, monkeypatch, seeded_workspace
) -> None:
    _, ws = seeded_workspace

    def boom(_workspace_id: str) -> None:
        raise RuntimeError("redis offline")

    monkeypatch.setattr(category_cache, "invalidate_resolved_categories", boom)

    override_id = await CategoryOverrideService(db).upsert(
        CategoryOverrideConfig(workspace_id=ws.id, template_key="moradia", label_override="Casa")
    )
    assert override_id  # write commitou apesar da falha de invalidação


@pytest.mark.asyncio
async def test_api_upsert_invalidates_cache_end_to_end(
    db: AsyncSession, client, fake_redis: _FakeRedis, seeded_workspace
) -> None:
    user, ws = seeded_workspace
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"

    list_resp = await client.get(f"/api/workspaces/{ws.id}/config/category-overrides/resolved")
    assert list_resp.status_code == 200
    assert _cached_keys(fake_redis)

    put_resp = await client.put(
        f"/api/workspaces/{ws.id}/config/category-overrides/moradia",
        json={"name": "Casa Premium"},
    )
    assert put_resp.status_code == 200, put_resp.text
    assert put_resp.json()["name"] == "Casa Premium"

    refreshed = await db.run_sync(lambda s: resolve_categories(ws.id, s))
    assert next(c.label for c in refreshed if c.key == "moradia") == "Casa Premium"
