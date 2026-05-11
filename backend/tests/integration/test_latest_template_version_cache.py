"""Integration: cache Redis de ``latest_template_version`` — miss/hit/invalidate/fallback (A11.cat-overrides-ux follow-up)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.category_template import CategoryTemplate
from backend.app.services import category_cache
from backend.app.services.category_resolver import (
    ACTIVE_TEMPLATE_VERSION,
    get_latest_template_version,
)


class _FakeRedis:
    """Stub in-process: get/set/delete via dict — exercita o path completo do cache."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, str]] = []

    def get(self, key: str) -> str | None:
        self.get_calls.append(key)
        return self._store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.set_calls.append((key, value))
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


_GLOBAL_KEY = "categories:latest_template_version"


def _template_row(version: int, key: str) -> CategoryTemplate:
    now = datetime.now(timezone.utc)
    return CategoryTemplate(
        id=str(uuid.uuid4()),
        template_version=version,
        key=key,
        label=key.capitalize(),
        category_type="expense",
        default_keywords=[],
        sort_order=1,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture
async def seeded_templates(db: AsyncSession) -> None:
    db.add(_template_row(1, "moradia_v1"))
    db.add(_template_row(2, "moradia_v2"))
    await db.commit()


@pytest.fixture
def fake_redis(monkeypatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_miss_populates_cache(
    db: AsyncSession, fake_redis: _FakeRedis, seeded_templates
) -> None:
    assert fake_redis.get(_GLOBAL_KEY) is None
    version = await db.run_sync(lambda s: get_latest_template_version(s))
    assert version == 2
    assert fake_redis._store.get(_GLOBAL_KEY) == "2"


@pytest.mark.asyncio
async def test_hit_skips_db_query(
    db: AsyncSession, fake_redis: _FakeRedis, seeded_templates
) -> None:
    # Primeiro acesso popula
    await db.run_sync(lambda s: get_latest_template_version(s))
    # Sobrescreve cache com valor diverso do DB para provar que o read não tocou o DB
    fake_redis._store[_GLOBAL_KEY] = "42"
    cached = await db.run_sync(lambda s: get_latest_template_version(s))
    assert cached == 42, "leitura subsequente deveria vir do cache, não do DB"


@pytest.mark.asyncio
async def test_invalidate_forces_db_refresh(
    db: AsyncSession, fake_redis: _FakeRedis, seeded_templates
) -> None:
    await db.run_sync(lambda s: get_latest_template_version(s))
    assert fake_redis._store.get(_GLOBAL_KEY) == "2"

    category_cache.invalidate_latest_template_version()

    assert _GLOBAL_KEY not in fake_redis._store
    refreshed = await db.run_sync(lambda s: get_latest_template_version(s))
    assert refreshed == 2
    assert fake_redis._store.get(_GLOBAL_KEY) == "2"


@pytest.mark.asyncio
async def test_redis_offline_falls_back_to_db(
    db: AsyncSession, monkeypatch, seeded_templates
) -> None:
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: None)
    version = await db.run_sync(lambda s: get_latest_template_version(s))
    assert version == 2


@pytest.mark.asyncio
async def test_redis_get_exception_falls_back_to_db(
    db: AsyncSession, monkeypatch, seeded_templates
) -> None:
    class _Broken:
        def get(self, key: str) -> str | None:
            raise RuntimeError("redis down mid-flight")

        def set(self, key: str, value: str, ex: int | None = None) -> None:
            raise RuntimeError("still broken")

        def delete(self, *keys: str) -> int:
            return 0

    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: _Broken())
    version = await db.run_sync(lambda s: get_latest_template_version(s))
    assert version == 2


@pytest.mark.asyncio
async def test_empty_db_returns_active_version(db: AsyncSession, fake_redis: _FakeRedis) -> None:
    """Sem rows no DB → cai no ACTIVE_TEMPLATE_VERSION e cacheia."""
    version = await db.run_sync(lambda s: get_latest_template_version(s))
    assert version == ACTIVE_TEMPLATE_VERSION
    assert fake_redis._store.get(_GLOBAL_KEY) == str(ACTIVE_TEMPLATE_VERSION)


def test_set_and_get_round_trip(fake_redis: _FakeRedis) -> None:
    assert category_cache.get_latest_template_version() is None
    category_cache.set_latest_template_version(3)
    assert category_cache.get_latest_template_version() == 3
    category_cache.invalidate_latest_template_version()
    assert category_cache.get_latest_template_version() is None


def test_parse_failure_returns_none(fake_redis: _FakeRedis) -> None:
    fake_redis._store[_GLOBAL_KEY] = "not-an-int"
    assert category_cache.get_latest_template_version() is None
