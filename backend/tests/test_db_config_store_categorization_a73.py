"""DBConfigStore.get_categorization + get_institutions wiring (A7.3 · ADR-137)."""

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
from backend.app.models.institution_catalog import InstitutionCatalog
from backend.app.services import institution_resolver
from backend.app.services.db_config_store import DBConfigStore
from backend.app.services.storage import category_cache
from pipeline.domain.types.config import CategorizationConfig, InstitutionsCatalog


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_dbcs_a73.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


@pytest.fixture
def no_redis(monkeypatch):
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: None)
    monkeypatch.setattr(institution_resolver, "_get_redis_safe", lambda: None)


def _seed_template(session_factory) -> None:
    rows = [
        ("moradia", "Moradia", "expense", ["ALUGUEL", "IPTU"], 1),
        ("alimentacao", "Alimentação", "expense", ["MERCADO"], 2),
        ("receita_pj", "Receita PJ", "income", ["NOTA FISCAL"], 3),
    ]
    with session_factory() as s:
        for key, label, ctype, kw, order in rows:
            s.add(
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
        s.commit()


def _seed_institution(session_factory) -> None:
    with session_factory() as s:
        s.add(
            InstitutionCatalog(
                id=str(uuid.uuid4()),
                code="itau",
                name="Itaú",
                category="bank",
                metadata_json={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        s.commit()


def _seed_override(session_factory, *, ws_id, key, **fields) -> None:
    with session_factory() as s:
        s.add(
            WorkspaceCategoryOverride(
                id=str(uuid.uuid4()),
                workspace_id=ws_id,
                template_key=key,
                label_override=fields.get("label_override"),
                keywords_override=fields.get("keywords_override"),
                monthly_cap_brl_cents_override=fields.get("monthly_cap_brl_cents_override"),
                disabled=fields.get("disabled", False),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        s.commit()


WS = "ws-a73"


class TestGetCategorization:
    def test_returns_typed_config(self, sync_db, no_redis):
        _seed_template(sync_db)
        with sync_db() as s:
            cfg = DBConfigStore(s).get_categorization(WS)
        assert isinstance(cfg, CategorizationConfig)
        assert set(cfg.categories.keys()) == {"moradia", "alimentacao", "receita_pj"}

    def test_overrides_applied(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(sync_db, ws_id=WS, key="moradia", label_override="Casa")
        with sync_db() as s:
            cfg = DBConfigStore(s).get_categorization(WS)
        assert cfg.categories["moradia"].name == "Casa"
        assert cfg.categories["moradia"].keywords == ("ALUGUEL", "IPTU")

    def test_disabled_filtered(self, sync_db, no_redis):
        _seed_template(sync_db)
        _seed_override(sync_db, ws_id=WS, key="moradia", disabled=True)
        with sync_db() as s:
            cfg = DBConfigStore(s).get_categorization(WS)
        assert "moradia" not in cfg.categories
        assert "alimentacao" in cfg.categories

    def test_returns_none_when_no_template_no_legacy(self, sync_db, no_redis):
        with sync_db() as s:
            cfg = DBConfigStore(s).get_categorization(WS)
        assert cfg is None

    def test_keywords_propagated_as_tuple(self, sync_db, no_redis):
        _seed_template(sync_db)
        with sync_db() as s:
            cfg = DBConfigStore(s).get_categorization(WS)
        moradia = cfg.categories["moradia"]
        assert isinstance(moradia.keywords, tuple)
        assert moradia.keywords == ("ALUGUEL", "IPTU")


class TestGetInstitutions:
    def test_returns_catalog_from_db(self, sync_db, no_redis):
        _seed_institution(sync_db)
        with sync_db() as s:
            catalog = DBConfigStore(s).get_institutions()
        assert isinstance(catalog, InstitutionsCatalog)
        assert "itau" in catalog.institutions
        assert catalog.institutions["itau"].name == "Itaú"

    def test_returns_empty_catalog_without_seed(self, sync_db, no_redis):
        with sync_db() as s:
            catalog = DBConfigStore(s).get_institutions()
        assert catalog.institutions == {}
