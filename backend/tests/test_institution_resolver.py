"""``institution_resolver`` — global catalog read + cache (A7.3 · ADR-137)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.institution_catalog import InstitutionCatalog
from backend.app.services import institution_resolver


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_inst_resolver.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


@pytest.fixture
def no_redis(monkeypatch):
    monkeypatch.setattr(institution_resolver, "_get_redis_safe", lambda: None)


def _seed_catalog(session_factory, items: list[dict]) -> None:
    with session_factory() as s:
        for item in items:
            s.add(
                InstitutionCatalog(
                    id=str(uuid.uuid4()),
                    code=item["code"],
                    name=item["name"],
                    default_parser=item.get("default_parser"),
                    category=item.get("category", "bank"),
                    metadata_json=item.get("metadata_json") or {},
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
        s.commit()


class TestResolveInstitutions:
    def test_returns_empty_catalog_when_no_rows(self, sync_db, no_redis):
        with sync_db() as s:
            catalog = institution_resolver.resolve_institutions(s)
        assert catalog.institutions == {}

    def test_returns_catalog_with_rows(self, sync_db, no_redis):
        _seed_catalog(
            sync_db,
            [
                {"code": "itau", "name": "Itaú", "category": "bank"},
                {"code": "c6bank", "name": "C6 Bank", "category": "bank"},
                {"code": "binance", "name": "Binance", "category": "exchange"},
            ],
        )
        with sync_db() as s:
            catalog = institution_resolver.resolve_institutions(s)
        assert set(catalog.institutions.keys()) == {"itau", "c6bank", "binance"}
        assert catalog.institutions["itau"].name == "Itaú"
        assert catalog.institutions["binance"].metadata.get("category") == "exchange"

    def test_default_parser_propagates(self, sync_db, no_redis):
        _seed_catalog(
            sync_db,
            [
                {"code": "itau", "name": "Itaú", "default_parser": "itau_xls"},
            ],
        )
        with sync_db() as s:
            catalog = institution_resolver.resolve_institutions(s)
        assert catalog.institutions["itau"].parser == "itau_xls"


class FakeRedisClient:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def delete(self, key):
        self.store.pop(key, None)


class TestCacheBehavior:
    def test_cache_hit_skips_db(self, sync_db, monkeypatch):
        fake = FakeRedisClient()
        monkeypatch.setattr(institution_resolver, "_get_redis_safe", lambda: fake)

        _seed_catalog(sync_db, [{"code": "itau", "name": "Itaú"}])
        with sync_db() as s:
            first = institution_resolver.resolve_institutions(s)

        # delete underlying rows
        with sync_db() as s:
            for r in s.query(InstitutionCatalog).all():
                s.delete(r)
            s.commit()

        # cache hit returns previous value
        with sync_db() as s:
            second = institution_resolver.resolve_institutions(s)
        assert set(first.institutions.keys()) == set(second.institutions.keys())

    def test_invalidate_forces_re_read(self, sync_db, monkeypatch):
        fake = FakeRedisClient()
        monkeypatch.setattr(institution_resolver, "_get_redis_safe", lambda: fake)

        _seed_catalog(sync_db, [{"code": "itau", "name": "Itaú"}])
        with sync_db() as s:
            institution_resolver.resolve_institutions(s)

        # Add new row + invalidate
        _seed_catalog(sync_db, [{"code": "c6bank", "name": "C6 Bank"}])
        institution_resolver.invalidate_catalog()

        with sync_db() as s:
            refreshed = institution_resolver.resolve_institutions(s)
        assert set(refreshed.institutions.keys()) == {"itau", "c6bank"}
