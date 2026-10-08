"""Regressão — `codigo_rfb` composto estoura a coluna em Postgres e parte a identidade entre eras.

O E1.5a emite o código do imóvel como `Grupo-Código` (`'01-11'`, desde a era 1.4.1 do
prompt) ou como código plano (`'11'`) — o mesmo apartamento em duas grafias. `property_identity.codigo_rfb` é `String(4)`: em Postgres o INSERT de `'01-12'`
levanta `StringDataRightTruncation` e derruba o E1.5c, e o SQLite desta suíte aceita
calado. Por isso a largura é lida do model, nunca do motor.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PropertyIdentity, User, Workspace
from backend.app.services.db_property_identity_resolver import DBPropertyIdentityResolver
from pipeline.domain.services.property_identity_enricher import enrich_imoveis_with_property_ids
from pipeline.domain.services.property_identity_mint import MINT_WITHOUT_CANONICAL_ENV

_LARGURA_DA_COLUNA = PropertyIdentity.__table__.c.codigo_rfb.type.length
_BASE_TS = datetime(2026, 5, 16, tzinfo=timezone.utc)
_TITULAR = "titular_exemplo"
_SEM_VIA = "CONDOMINIO EXEMPLO - APTO 12"
_CASA = "CASA - Rua Exemplo, 100"
_APTO = "APARTAMENTO - Rua Exemplo, 100"


@pytest.fixture
def sync_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def workspace_id(sync_db) -> str:
    with sync_db() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=f"u-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="x",
            full_name="Test",
        )
        session.add(user)
        session.flush()
        ws = Workspace(id=str(uuid.uuid4()), name="Test WS", owner_id=user.id)
        session.add(ws)
        session.commit()
        return ws.id


def _imovel(codigo: str, descricao: str, ano: int = 2025) -> dict:
    return {
        "descricao": descricao,
        "proprietario": _TITULAR,
        "codigo_rfb": codigo,
        "ano_referencia": ano,
        "eixo_autoridade": "secao",
    }


def _enrich(sync_db, workspace_id: str, *imoveis: dict) -> list[dict]:
    consolidated = {"imoveis_consolidados": list(imoveis)}
    with sync_db() as session:
        resolver = DBPropertyIdentityResolver(session=session)
        enrich_imoveis_with_property_ids(consolidated, resolver=resolver, workspace_id=workspace_id)
    return consolidated["imoveis_consolidados"]


def _seed(sync_db, workspace_id: str, codigo: str, descricao: str, canonical, minuto=0) -> str:
    with sync_db() as session:
        row = PropertyIdentity(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            titular_key=_TITULAR,
            codigo_rfb=codigo,
            endereco_canonical=canonical,
            first_seen_year=2024,
            descricao_sample=descricao,
            low_confidence=canonical is None,
            created_at=_BASE_TS + timedelta(minutes=minuto),
        )
        session.add(row)
        session.commit()
        return row.id


def _codigos_gravados(sync_db, workspace_id: str) -> list[str]:
    stmt = select(PropertyIdentity.codigo_rfb).where(PropertyIdentity.workspace_id == workspace_id)
    with sync_db() as session:
        return list(session.execute(stmt).scalars())


@pytest.mark.parametrize(
    ("emitido", "gravado"),
    [("01-11", "11"), ("01-12", "12"), ("12", "12"), ("1", "01"), ("G01", "01")],
)
def test_toda_grafia_emitida_vira_row_que_cabe_na_coluna(sync_db, workspace_id, emitido, gravado):
    """Workspace novo + descrição com via e número vai a INSERT: o código tem de caber."""
    _enrich(sync_db, workspace_id, _imovel(emitido, _CASA))
    codigos = _codigos_gravados(sync_db, workspace_id)
    assert codigos == [gravado]
    assert all(len(codigo) <= _LARGURA_DA_COLUNA for codigo in codigos)


# Truncar corromperia a chave em silêncio; recusar o mint é o lado seguro (ADR-392 D2).
@pytest.mark.parametrize("emitido", ["11 - APARTAMENTO", "0111", "APTO"])
def test_codigo_que_nao_parseia_nao_vira_row(sync_db, workspace_id, emitido):
    """Sem sub-código legível não há chave: item vai a revisão, nada é gravado."""
    [item] = _enrich(sync_db, workspace_id, _imovel(emitido, _CASA))
    assert item["property_id"] is None
    assert item["needs_review"] is True
    assert _codigos_gravados(sync_db, workspace_id) == []


# A segunda row sem canonical torna o residual ambíguo: só a amostra byte-exata casa.
# `G01`/`1` são grafias do produtor legado (`bem["grupo"]` cru) e cabem em Postgres;
# `01-11` só existe em SQLite de dev, gravado antes do conserto.
@pytest.mark.parametrize(
    ("gravado", "emitido"),
    [("11", "01-11"), ("01-11", "11"), ("G01", "01"), ("1", "01")],
)
def test_amostra_byte_exata_casa_atravessando_a_grafia(sync_db, workspace_id, gravado, emitido):
    """A mesma descrição em outra era reencontra a row em vez de cair em revisão."""
    seeded = _seed(sync_db, workspace_id, gravado, _SEM_VIA, canonical=None)
    _seed(sync_db, workspace_id, gravado, "OUTRA DESCRICAO SEM VIA", canonical=None, minuto=1)
    [item] = _enrich(sync_db, workspace_id, _imovel(emitido, _SEM_VIA))
    assert item["property_id"] == seeded


def test_residual_unico_atravessa_a_grafia(sync_db, workspace_id):
    """ADR-392 D1: a única row viva sem canonical do par (titular, código) casa nas duas grafias."""
    seeded = _seed(
        sync_db, workspace_id, "12", "COMPRA DE CASA NO LOTEAMENTO FICTICIO", canonical=None
    )
    [item] = _enrich(sync_db, workspace_id, _imovel("01-12", _SEM_VIA))
    assert item["property_id"] == seeded


def test_estrito_escolhe_o_subtipo_entre_eras_no_mesmo_endereco(sync_db, workspace_id):
    """Apto e casa no mesmo lote (ADR-225 §Alternativas B): o loose devolveria o mais antigo."""
    _seed(sync_db, workspace_id, "11", _APTO, canonical="exemplo 100")
    casa = _seed(sync_db, workspace_id, "12", _CASA, canonical="exemplo 100", minuto=1)
    [item] = _enrich(sync_db, workspace_id, _imovel("01-12", _CASA))
    assert item["property_id"] == casa


def test_com_o_mint_religado_o_par_entre_eras_vira_uma_identidade(
    sync_db, workspace_id, monkeypatch
):
    """Pré-condição da âncora estruturada: religar o mint sem isto cunha uma identidade por grafia."""
    monkeypatch.setenv(MINT_WITHOUT_CANONICAL_ENV, "1")
    itens = _enrich(
        sync_db, workspace_id, _imovel("11", _SEM_VIA, ano=2024), _imovel("01-11", _SEM_VIA)
    )
    assert itens[0]["property_id"] == itens[1]["property_id"]
    assert _codigos_gravados(sync_db, workspace_id) == ["11"]


def test_sem_o_mint_o_par_sem_canonical_segue_sem_identidade(sync_db, workspace_id):
    """Necessário, não suficiente: sem row a casar e sem mint, a grafia única não junta o par."""
    itens = _enrich(
        sync_db, workspace_id, _imovel("11", _SEM_VIA, ano=2024), _imovel("01-11", _SEM_VIA)
    )
    assert [item["property_id"] for item in itens] == [None, None]
