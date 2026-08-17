"""ADR-385 — toda row viva historicamente gravável continua alcançável pelo resolver."""

# O corpus congela as FORMAS de `endereco_canonical` que cada era do
# canonicalizador chegou a gravar em produção, derivado da tabela de eras da
# ADR-385 e não da memória de quem escreve: mudança futura em `canonicalize()`
# que órfã uma dessas formas quebra este teste até existir passe de sweep
# correspondente. Formas anonimizadas — nenhum endereço, matrícula ou valor real.

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PropertyIdentity, User, Workspace
from backend.app.services.db_property_identity_resolver import DBPropertyIdentityResolver
from pipeline.domain.types.property_identity import PropertyLookupKey

_BASE_TS = datetime(2026, 5, 16, tzinfo=timezone.utc)

# era → forma gravada na coluna `endereco_canonical`. Ver §Tabela de eras da ADR-385.
ERA_FORMS = [
    pytest.param("8 0", id="era1-prefixo-monetario"),
    pytest.param(None, id="era2-bypass-sem-canonical"),
    pytest.param("mat:99999", id="era3-matricula"),
    pytest.param("qa:12345", id="era3-quintoandar"),
    pytest.param("iptu:123456", id="era3-iptu"),
    pytest.param("via exemplo 100", id="era4-via-numero"),
]

DESCRICAO = "CASA - VIA EXEMPLO 100, BAIRRO EXEMPLO - Matricula 99999"


@pytest.fixture
def sync_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _seed_workspace(sync_db) -> Workspace:
    with sync_db() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=f"u-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="x",
            full_name="Test",
        )
        session.add(user)
        session.flush()
        ws = Workspace(id=str(uuid.uuid4()), name="Test WS", owner_id=user.id, created_at=_BASE_TS)
        session.add(ws)
        session.commit()
        session.refresh(ws)
        return ws


def _seed_identity(session, workspace_id: str, canonical: str | None, **kwargs) -> str:
    row = PropertyIdentity(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        titular_key="titular_exemplo",
        codigo_rfb="12",
        endereco_canonical=canonical,
        first_seen_year=2024,
        descricao_sample=DESCRICAO,
        low_confidence=canonical is None,
        created_at=kwargs.get("created_at", _BASE_TS),
        superseded_at=kwargs.get("superseded_at"),
        superseded_by_id=kwargs.get("superseded_by_id"),
    )
    session.add(row)
    session.flush()
    return row.id


def _lookup(canonical: str | None) -> PropertyLookupKey:
    return PropertyLookupKey(
        titular_key="titular_exemplo", codigo_rfb="12", endereco_canonical=canonical
    )


@pytest.mark.parametrize("forma", ERA_FORMS)
def test_forma_historica_viva_e_alcancada_sem_inserir(sync_db, forma):
    """Row gravada por qualquer era, viva, é reencontrada — não vira duplicata."""
    ws = _seed_workspace(sync_db)
    with sync_db() as session:
        seeded = _seed_identity(session, ws.id, forma)
        session.commit()
        resolver = DBPropertyIdentityResolver(session=session)
        record = resolver.match_or_create(ws.id, _lookup(forma), 2025, DESCRICAO)
        assert record.property_id == seeded


@pytest.mark.parametrize("forma", ERA_FORMS)
def test_forma_historica_supersedida_resolve_para_a_vencedora(sync_db, forma):
    """Pós-sweep, o input que ainda casa a perdedora chega na vencedora pelo ponteiro."""
    ws = _seed_workspace(sync_db)
    with sync_db() as session:
        vencedora = _seed_identity(
            session, ws.id, "mat:99999", created_at=_BASE_TS + timedelta(days=2)
        )
        perdedora = _seed_identity(
            session,
            ws.id,
            forma,
            superseded_at=_BASE_TS + timedelta(days=3),
            superseded_by_id=vencedora,
        )
        session.commit()
        resolver = DBPropertyIdentityResolver(session=session)
        record = resolver.match_or_create(ws.id, _lookup(forma), 2025, DESCRICAO)
        assert record.property_id == vencedora
        assert record.property_id != perdedora


@pytest.mark.parametrize("forma", ERA_FORMS)
def test_ponteiro_orfao_nao_ressuscita_a_perdedora(sync_db, forma):
    """superseded_at setado + ponteiro NULL: o candidato é pulado, nunca devolvido."""
    ws = _seed_workspace(sync_db)
    with sync_db() as session:
        orfa = _seed_identity(session, ws.id, forma, superseded_at=_BASE_TS + timedelta(days=3))
        session.commit()
        resolver = DBPropertyIdentityResolver(session=session)
        record = resolver.match_or_create(ws.id, _lookup(forma), 2025, DESCRICAO)
        assert record is None or record.property_id != orfa


def _seed_cluster_do_dogfood(session, workspace_id: str) -> str:
    """Vencedora era-3 + as 3 perdedoras (1 era-1, 2 era-2) já supersedidas."""
    vencedora = _seed_identity(
        session, workspace_id, "mat:99999", created_at=_BASE_TS + timedelta(days=4)
    )
    for forma in ("8 0", None, None):
        _seed_identity(
            session,
            workspace_id,
            forma,
            superseded_at=_BASE_TS + timedelta(days=5),
            superseded_by_id=vencedora,
        )
    session.commit()
    return vencedora


def test_cluster_multi_era_converge_para_uma_unica_vencedora(sync_db):
    """As 3 formas do cluster real do dogfood resolvem todas para a mesma row."""
    ws = _seed_workspace(sync_db)
    with sync_db() as session:
        vencedora = _seed_cluster_do_dogfood(session, ws.id)
        resolver = DBPropertyIdentityResolver(session=session)
        for forma in ("8 0", None, "mat:99999"):
            record = resolver.match_or_create(ws.id, _lookup(forma), 2025, DESCRICAO)
            assert record.property_id == vencedora


def test_cluster_multi_era_nao_repovoa_o_workspace(sync_db):
    """Resolver as 3 formas não cria row nova — a população para de crescer."""
    ws = _seed_workspace(sync_db)
    with sync_db() as session:
        _seed_cluster_do_dogfood(session, ws.id)
        resolver = DBPropertyIdentityResolver(session=session)
        for forma in ("8 0", None, "mat:99999"):
            resolver.match_or_create(ws.id, _lookup(forma), 2025, DESCRICAO)
        rows = session.query(PropertyIdentity).filter_by(workspace_id=ws.id).all()
        assert len(rows) == 4
        assert len([r for r in rows if r.superseded_at is None]) == 1
