"""A classificação do usuário sobrevive ao re-upload ([[ADR-215]] · [[A40.l121]] · [[ADR-440]])."""

# Declarado pela ADR-215 e inexistente até a A40.l121 — é o gate que teria pego a regressão
# do prompt E1.5a 1.4.1: a descrição passou a ser só a discriminação, o endereço saiu dela, e
# o imóvel classificado pelo usuário perdeu a identidade sem aviso. Roda o produtor real
# (`consolidate_from_itens` + enricher) contra o resolver de DB; valores todos inventados.

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PropertyIdentity, User, Workspace
from backend.app.models.property_identity import WorkspacePropertyOverride
from backend.app.services.db_property_identity_resolver import DBPropertyIdentityResolver
from pipeline.domain.services.property_identity_enricher import enrich_imoveis_with_property_ids
from scripts.consolidate_baseline import consolidate_from_itens

# Era 1.3.0: o LLM dobrava os campos da ficha na descrição. Era 1.4.1: só a discriminação,
# e o endereço chega pela âncora que o parser da ficha grava no item do E1.5a.
_DOBRADA = "APARTAMENTO EXEMPLO - Rua Exemplo, 100 - APTO 1 - MATRICULA 999.999"
_LITERAL = "APARTAMENTO EXEMPLO"
_ANCORA = {"join": "valor", "logradouro": "Rua Exemplo", "numero": "100", "matricula": "999.999"}


@pytest.fixture
def sync_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _seed_workspace(sync_db) -> str:
    """Materializa os pais da FK ([[ADR-371]]): usuário e workspace."""
    with sync_db() as session:
        user = User(id=str(uuid.uuid4()), email="u@test.com", hashed_password="x", full_name="T")
        session.add(user)
        session.flush()
        ws = Workspace(id=str(uuid.uuid4()), name="WS", owner_id=user.id)
        session.add(ws)
        session.commit()
        return ws.id


def _itens(descricao: str, ancora: dict | None = None, codigo: str = "11") -> list[dict]:
    item = {
        "codigo": codigo,
        "descricao": descricao,
        "categoria_hint": "imovel",
        "secao": "bens_direitos",
        "valor_brl": "300000.00",
        "membro": "titular_exemplo",
        "ano": 2024,
    }
    return [{**item, "ancora_imovel": ancora} if ancora else item]


def _consolidar(session, workspace_id: str, itens: list[dict]) -> dict:
    base = consolidate_from_itens({"resumo": {"ano_referencia": 2024}, "itens": itens})
    resolver = DBPropertyIdentityResolver(session=session)
    enrich_imoveis_with_property_ids(base, resolver=resolver, workspace_id=workspace_id)
    return base["imoveis_consolidados"][0]


def _classificar(session, workspace_id: str, property_id: str) -> None:
    session.add(
        WorkspacePropertyOverride(
            workspace_id=workspace_id,
            property_id=property_id,
            classification="locado",
            override_source="user_manual",
        )
    )
    session.commit()


def _rows(session) -> int:
    return session.execute(select(func.count()).select_from(PropertyIdentity)).scalar_one()


def test_classificacao_sobrevive_ao_reupload_na_era_da_discriminacao_literal(sync_db) -> None:
    workspace_id = _seed_workspace(sync_db)
    with sync_db() as session:
        antes = _consolidar(session, workspace_id, _itens(_DOBRADA))
        _classificar(session, workspace_id, antes["property_id"])
        rows = _rows(session)
        depois = _consolidar(session, workspace_id, _itens(_LITERAL, _ANCORA))
        assert depois["property_id"] == antes["property_id"]
        assert _rows(session) == rows


def test_sem_ancora_o_colapso_volta(sync_db) -> None:
    """Contrafactual de [[ADR-440]]: reverter a âncora reproduz o defeito medido no U5."""
    workspace_id = _seed_workspace(sync_db)
    with sync_db() as session:
        antes = _consolidar(session, workspace_id, _itens(_DOBRADA))
        _classificar(session, workspace_id, antes["property_id"])
        depois = _consolidar(session, workspace_id, _itens(_LITERAL))
        assert antes["property_id"] is not None and depois["property_id"] is None


# O loose ignora o sub-código, e é por ele que a casa herdaria a row — e a classificação —
# do apartamento no mesmo endereço ([[ADR-225]] §Emenda 2026-10-08). O veto é do enricher.
_ANCORA_CASA = {"join": "valor", "logradouro": "Rua Exemplo", "numero": "100"}


def test_casa_no_endereco_do_apartamento_nao_herda_a_row_dele(sync_db) -> None:
    workspace_id = _seed_workspace(sync_db)
    with sync_db() as session:
        apto = _consolidar(session, workspace_id, _itens(_DOBRADA))
        _classificar(session, workspace_id, apto["property_id"])
        casa = _consolidar(session, workspace_id, _itens("CASA", _ANCORA_CASA, codigo="12"))
        assert casa["property_id"] not in (None, apto["property_id"])


def test_sem_o_veto_de_subcodigo_a_casa_herda_a_row(sync_db, monkeypatch) -> None:
    """Contrafactual: é o veto de sub-código que separa, não o match estrito."""
    from pipeline.domain.services import property_identity_enricher as enricher

    monkeypatch.setattr(enricher, "subcodigos_divergem", lambda a, b: False)
    workspace_id = _seed_workspace(sync_db)
    with sync_db() as session:
        apto = _consolidar(session, workspace_id, _itens(_DOBRADA))
        casa = _consolidar(session, workspace_id, _itens("CASA", _ANCORA_CASA, codigo="12"))
        assert casa["property_id"] == apto["property_id"]
