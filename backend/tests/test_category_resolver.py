"""``category_resolver`` — merge template + overrides + cache (A7.3 · ADR-137)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.category_template import (
    CategoryTemplate,
    WorkspaceCategoryOverride,
)
from backend.app.services import category_cache
from backend.app.services.category_resolver import (
    METADATA_TEMPLATE_KEY,
    ResolvedCategory,
    get_categorization_metadata,
    resolve_categories,
)


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_cat_resolver.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


@pytest.fixture
def no_redis(monkeypatch):
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: None)


def _seed_template(
    session_factory,
    *,
    template_version: int = 1,
    rows: list[dict] | None = None,
) -> None:
    rows = rows or [
        {
            "key": "moradia",
            "label": "Moradia",
            "category_type": "expense",
            "default_keywords": ["ALUGUEL", "IPTU"],
            "sort_order": 1,
        },
        {
            "key": "alimentacao",
            "label": "Alimentação",
            "category_type": "expense",
            "default_keywords": ["MERCADO"],
            "sort_order": 2,
        },
        {
            "key": "receita_pj",
            "label": "Receita PJ",
            "category_type": "income",
            "default_keywords": ["NOTA FISCAL"],
            "sort_order": 3,
        },
    ]
    with session_factory() as s:
        for r in rows:
            s.add(
                CategoryTemplate(
                    id=str(uuid.uuid4()),
                    template_version=template_version,
                    key=r["key"],
                    parent_key=r.get("parent_key"),
                    label=r["label"],
                    category_type=r["category_type"],
                    default_keywords=r.get("default_keywords") or [],
                    default_monthly_cap_brl_cents=r.get("default_monthly_cap_brl_cents"),
                    sort_order=r.get("sort_order", 0),
                    metadata_json=r.get("metadata_json") or {},
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
        s.commit()


def _seed_metadata_row(session_factory, *, payload: dict) -> None:
    with session_factory() as s:
        s.add(
            CategoryTemplate(
                id=str(uuid.uuid4()),
                template_version=1,
                key=METADATA_TEMPLATE_KEY,
                label="(metadata)",
                category_type="expense",
                default_keywords=[],
                sort_order=9999,
                metadata_json=payload,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        s.commit()


def _seed_override(
    session_factory,
    *,
    workspace_id: str,
    template_key: str,
    label_override: str | None = None,
    keywords_override: list[str] | None = None,
    monthly_cap_brl_cents_override: int | None = None,
    disabled: bool = False,
) -> None:
    with session_factory() as s:
        s.add(
            WorkspaceCategoryOverride(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                template_key=template_key,
                label_override=label_override,
                keywords_override=keywords_override,
                monthly_cap_brl_cents_override=monthly_cap_brl_cents_override,
                disabled=disabled,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        s.commit()


WS_A = "ws-a"
WS_B = "ws-b"


class TestResolveCategoriesNoOverrides:
    def test_returns_template_only(self, sync_db, no_redis):
        _seed_template(sync_db)
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        assert {c.key for c in resolved} == {"moradia", "alimentacao", "receita_pj"}
        moradia = next(c for c in resolved if c.key == "moradia")
        assert moradia.label == "Moradia"
        assert moradia.keywords == ("ALUGUEL", "IPTU")
        assert moradia.monthly_cap_brl_cents is None
        assert moradia.disabled is False

    def test_returns_typed_dataclass(self, sync_db, no_redis):
        _seed_template(sync_db)
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        assert all(isinstance(c, ResolvedCategory) for c in resolved)

    def test_filters_metadata_row_from_resolved(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_metadata_row(sync_db, payload={"pj_source_mapping": {"X": "Y"}})
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        assert all(c.key != METADATA_TEMPLATE_KEY for c in resolved)
        assert {c.key for c in resolved} == {"moradia", "alimentacao", "receita_pj"}

    def test_returns_empty_when_no_template(self, sync_db, no_redis):
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        assert resolved == []


class TestResolveCategoriesWithOverrides:
    def test_label_override(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="moradia",
            label_override="Casa",
        )
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        moradia = next(c for c in resolved if c.key == "moradia")
        assert moradia.label == "Casa"
        # keywords unchanged from template
        assert moradia.keywords == ("ALUGUEL", "IPTU")

    def test_keywords_override(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="moradia",
            keywords_override=["NOVO_ALUGUEL", "CUSTO_FIXO"],
        )
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        moradia = next(c for c in resolved if c.key == "moradia")
        assert moradia.keywords == ("NOVO_ALUGUEL", "CUSTO_FIXO")
        # label unchanged
        assert moradia.label == "Moradia"

    def test_monthly_cap_override(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="alimentacao",
            monthly_cap_brl_cents_override=300000,  # R$ 3000.00
        )
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        cat = next(c for c in resolved if c.key == "alimentacao")
        assert cat.monthly_cap_brl_cents == 300000

    def test_disabled_override_filters_category(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="moradia",
            disabled=True,
        )
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        keys = {c.key for c in resolved}
        assert "moradia" not in keys
        assert "alimentacao" in keys

    def test_overrides_isolated_per_workspace(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="moradia",
            label_override="Casa A",
        )
        _seed_override(
            sync_db,
            workspace_id=WS_B,
            template_key="moradia",
            label_override="Casa B",
        )
        with sync_db() as s:
            resolved_a = resolve_categories(WS_A, s)
            resolved_b = resolve_categories(WS_B, s)
        ma = next(c for c in resolved_a if c.key == "moradia")
        mb = next(c for c in resolved_b if c.key == "moradia")
        assert ma.label == "Casa A"
        assert mb.label == "Casa B"

    def test_multi_field_override(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="moradia",
            label_override="Casa Principal",
            keywords_override=["X"],
            monthly_cap_brl_cents_override=500000,
        )
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        m = next(c for c in resolved if c.key == "moradia")
        assert m.label == "Casa Principal"
        assert m.keywords == ("X",)
        assert m.monthly_cap_brl_cents == 500000


class TestCategorizationMetadata:
    def test_returns_metadata_blob(self, sync_db):
        _seed_template(sync_db)
        _seed_metadata_row(
            sync_db,
            payload={
                "pj_source_mapping": {"ARVO": "Arvo (PJ)"},
                "internal_transfer_patterns": ["bx Aut Poupanca"],
            },
        )
        with sync_db() as s:
            metadata = get_categorization_metadata(s)
        assert metadata["pj_source_mapping"] == {"ARVO": "Arvo (PJ)"}
        assert metadata["internal_transfer_patterns"] == ["bx Aut Poupanca"]

    def test_returns_empty_when_no_metadata_row(self, sync_db):
        _seed_template(sync_db)  # no metadata row
        with sync_db() as s:
            metadata = get_categorization_metadata(s)
        assert metadata == {}


class TestSortOrder:
    def test_resolved_respects_sort_order(self, sync_db, no_redis):
        _seed_template(
            sync_db,
            rows=[
                {
                    "key": "z_last",
                    "label": "Z",
                    "category_type": "expense",
                    "default_keywords": [],
                    "sort_order": 99,
                },
                {
                    "key": "a_first",
                    "label": "A",
                    "category_type": "expense",
                    "default_keywords": [],
                    "sort_order": 1,
                },
            ],
        )
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        keys = [c.key for c in resolved]
        assert keys == ["a_first", "z_last"]


class TestKeywordsEmptyOverride:
    def test_empty_list_override_removes_keywords(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="moradia",
            keywords_override=[],
        )
        with sync_db() as s:
            resolved = resolve_categories(WS_A, s)
        m = next(c for c in resolved if c.key == "moradia")
        assert m.keywords == ()


class FakeRedisClient:
    """Fake Redis para testes de cache — não é MagicMock."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.deletes: list[str] = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def delete(self, key):
        self.deletes.append(key)
        self.store.pop(key, None)

    def scan_iter(self, match=None):
        prefix = match.replace("*", "") if match else ""
        return [k for k in list(self.store) if k.startswith(prefix)]


class TestCacheIntegration:
    def test_cache_hit_skips_db(self, sync_db, monkeypatch):
        _seed_template(sync_db)
        fake = FakeRedisClient()
        monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: fake)

        with sync_db() as s:
            first = resolve_categories(WS_A, s)
        # Now corrupt template — second call should still return cached
        with sync_db() as s:
            for row in s.query(CategoryTemplate).all():
                s.delete(row)
            s.commit()
        with sync_db() as s:
            second = resolve_categories(WS_A, s)
        assert {c.key for c in first} == {c.key for c in second}

    def test_cache_invalidation_forces_db_read(self, sync_db, monkeypatch):
        _seed_template(sync_db)
        fake = FakeRedisClient()
        monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: fake)

        with sync_db() as s:
            first = resolve_categories(WS_A, s)
        assert len(first) == 3

        category_cache.invalidate_resolved_categories(WS_A)
        # Add override; cache invalidated so next read must reflect it
        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="moradia",
            label_override="Casa Renomeada",
        )
        with sync_db() as s:
            second = resolve_categories(WS_A, s)
        moradia = next(c for c in second if c.key == "moradia")
        assert moradia.label == "Casa Renomeada"

    def test_cache_separates_workspaces(self, sync_db, monkeypatch):
        _seed_template(sync_db)
        fake = FakeRedisClient()
        monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: fake)

        _seed_override(
            sync_db,
            workspace_id=WS_A,
            template_key="moradia",
            label_override="A's Moradia",
        )
        with sync_db() as s:
            resolve_categories(WS_A, s)
        # WS_B should produce different result
        with sync_db() as s:
            resolved_b = resolve_categories(WS_B, s)
        m_b = next(c for c in resolved_b if c.key == "moradia")
        assert m_b.label == "Moradia"
