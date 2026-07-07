"""``DBInstitutionCatalogProvider`` — adapter DB do protocol (A33.l8 · ADR-137).

Critério de aceite da lane: instituição nova no ``institution_catalog``
reflete no bloco injetado no prompt sem editar código.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401 — registra tabelas no metadata
from backend.app.core.database import Base
from backend.app.models.institution_catalog import InstitutionCatalog
from backend.app.services.institution_catalog_provider import DBInstitutionCatalogProvider
from pipeline.llm.institution_catalog import INSURANCE_CATEGORY, render_institution_catalog


@pytest.fixture
def session(monkeypatch):
    # Sem Redis no teste: resolver cai direto no DB (falha aberta) e não lê
    # cache "institution_catalog:global" de um Redis local do dev.
    monkeypatch.setattr("backend.app.services.institution_resolver._get_redis_safe", lambda: None)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    yield db
    db.close()
    engine.dispose()


def _seed(db, code: str, name: str, category: str) -> None:
    db.add(InstitutionCatalog(code=code, name=name, category=category))
    db.commit()


def test_list_institutions_reflete_rows_do_db(session):
    _seed(session, "bancoalfa", "Banco Alfa", "bank")
    _seed(session, "seguradoragama", "Seguradora Gama", INSURANCE_CATEGORY)

    entries = DBInstitutionCatalogProvider(session=session).list_institutions()

    by_code = {e.code: e for e in entries}
    assert by_code["bancoalfa"].name == "Banco Alfa"
    assert by_code["bancoalfa"].category == "bank"
    assert by_code["seguradoragama"].category == INSURANCE_CATEGORY


def test_instituicao_nova_reflete_no_bloco_do_prompt_sem_editar_codigo(session):
    provider = DBInstitutionCatalogProvider(session=session)
    _seed(session, "bancoalfa", "Banco Alfa", "bank")
    assert "bancodelta" not in render_institution_catalog(provider)

    _seed(session, "bancodelta", "Banco Delta", "bank")

    block = render_institution_catalog(provider, exclude_categories=(INSURANCE_CATEGORY,))
    assert "- bancodelta (Banco Delta)" in block


def test_catalogo_vazio_nao_quebra_render(session):
    provider = DBInstitutionCatalogProvider(session=session)
    block = render_institution_catalog(provider)
    assert isinstance(block, str) and block, "fallback documentado, nunca crash"
