"""build_config_overrides_from_db — A7.3 wiring (categorization+institutions via resolver)."""

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
from backend.app.services import category_cache, institution_resolver
from backend.app.services.pipeline_adapter import build_config_overrides_from_db
from backend.app.services.category_resolver import METADATA_TEMPLATE_KEY


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_pa_a73.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


@pytest.fixture
def no_redis(monkeypatch):
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: None)
    monkeypatch.setattr(institution_resolver, "_get_redis_safe", lambda: None)


def _seed_template(session_factory, with_metadata=False) -> None:
    rows = [
        ("moradia", "Moradia", "expense", ["ALUGUEL"], 1),
        ("receita_pj", "Receita PJ", "income", ["ARVO"], 2),
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
        if with_metadata:
            s.add(
                CategoryTemplate(
                    id=str(uuid.uuid4()),
                    template_version=1,
                    key=METADATA_TEMPLATE_KEY,
                    label="metadata",
                    category_type="expense",
                    default_keywords=[],
                    sort_order=999,
                    metadata_json={
                        "internal_transfer_patterns": ["Pagto Cobranca"],
                        "pj_source_mapping": {"ARVO": "Arvo (PJ)"},
                    },
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
        s.commit()


def _seed_institutions(session_factory) -> None:
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
        s.add(
            InstitutionCatalog(
                id=str(uuid.uuid4()),
                code="c6bank",
                name="C6 Bank",
                category="bank",
                metadata_json={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        s.commit()


WS = "ws-pa-a73"


def test_build_overrides_includes_categorization_from_template(
    sync_db, no_redis
):
    _seed_template(sync_db)
    with sync_db() as s:
        overrides = build_config_overrides_from_db(WS, db=s)
    assert "categorization.json" in overrides
    cat = overrides["categorization.json"]
    assert cat["expense_keywords"]["moradia"] == ["ALUGUEL"]
    assert cat["income_keywords"]["receita_pj"] == ["ARVO"]


def test_build_overrides_includes_metadata_aux_keys(sync_db, no_redis):
    _seed_template(sync_db, with_metadata=True)
    with sync_db() as s:
        overrides = build_config_overrides_from_db(WS, db=s)
    cat = overrides["categorization.json"]
    assert cat["internal_transfer_patterns"] == ["Pagto Cobranca"]
    assert cat["pj_source_mapping"] == {"ARVO": "Arvo (PJ)"}


def test_build_overrides_categorization_with_workspace_override(
    sync_db, no_redis
):
    _seed_template(sync_db)
    with sync_db() as s:
        s.add(
            WorkspaceCategoryOverride(
                id=str(uuid.uuid4()),
                workspace_id=WS,
                template_key="moradia",
                keywords_override=["NOVA_KW"],
                disabled=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        s.commit()
    with sync_db() as s:
        overrides = build_config_overrides_from_db(WS, db=s)
    assert overrides["categorization.json"]["expense_keywords"]["moradia"] == [
        "NOVA_KW"
    ]


def test_build_overrides_includes_institutions_from_catalog(sync_db, no_redis):
    _seed_institutions(sync_db)
    with sync_db() as s:
        overrides = build_config_overrides_from_db(WS, db=s)
    assert "institutions.json" in overrides
    canonical = overrides["institutions.json"]["banco_canonical"]
    assert canonical["itau"] == "Itaú"
    assert canonical["c6bank"] == "C6 Bank"


def test_build_overrides_omits_empty_sources(sync_db, no_redis):
    """Sem template nem instituições → keys ausentes (null filter)."""
    with sync_db() as s:
        overrides = build_config_overrides_from_db(WS, db=s)
    assert "categorization.json" not in overrides
    assert "institutions.json" not in overrides
