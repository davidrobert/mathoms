"""E1.5c ponta a ponta — `codigo_rfb` composto chega ao banco e ao dedup na forma canônica.

O produtor do campo e os três alimentadores da policy de dedup precisam ver a MESMA forma:
com `'01-11'` cru o dedup lê o apartamento como genérico e o funde na casa `'12'` do mesmo
endereço ([[ADR-225]] §Emenda 2026-10-08). Mora em `tests/` porque importa o stage, que o
filtro `pipeline_lib` da suíte do backend não cobre (ADR-210).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PropertyIdentity, User, Workspace
from backend.app.services.db_property_identity_resolver import DBPropertyIdentityResolver
from backend.app.services.real_estate_e5_integration import _dedup_entries
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.domain.services.imoveis_dedup import resolve_dedup_winner_by_property_id
from scripts.consolidate_baseline import consolidate_from_itens, main_with_store

_LARGURA_DA_COLUNA = PropertyIdentity.__table__.c.codigo_rfb.type.length
_BASE_TS = datetime(2026, 5, 16, tzinfo=timezone.utc)
_TITULAR = "titular_exemplo"
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


def _seed(sync_db, workspace_id: str, codigo: str, descricao: str, minuto: int = 0) -> str:
    with sync_db() as session:
        row = PropertyIdentity(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            titular_key=_TITULAR,
            codigo_rfb=codigo,
            endereco_canonical="exemplo 100",
            first_seen_year=2024,
            descricao_sample=descricao,
            low_confidence=False,
            created_at=_BASE_TS + timedelta(minutes=minuto),
        )
        session.add(row)
        session.commit()
        return row.id


def _baseline_e15a(*itens: tuple[str, str]) -> dict:
    return {
        "itens": [
            {
                "codigo": codigo,
                "descricao": descricao,
                "categoria_hint": "imovel",
                "secao": "bens_direitos",
                "valor_brl": "100000.00",
                "membro": _TITULAR,
                "ano": 2025,
            }
            for codigo, descricao in itens
        ],
        "resumo": {"ano_referencia": 2025},
    }


def _run_consolidate(sync_db, workspace_id: str, tmp_path, baseline: dict) -> dict:
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", baseline)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    (tmp_path / "config" / "family_members.json").write_text("{}")
    with sync_db() as session:
        resolver = DBPropertyIdentityResolver(session=session)
        ctx = WorkspaceContext(
            root=tmp_path,
            artifact_store=store,
            workspace_id=workspace_id,
            property_identity_resolver=resolver,
        )
        assert main_with_store(ctx)["success"] is True
    return store.read("E1.5c", "baseline_patrimonial")


def test_item_do_e15a_chega_ao_banco_na_forma_canonica(sync_db, workspace_id, tmp_path):
    """Produtor real → enricher → resolver DB: o artefato e a row carregam o sub-código."""
    baseline = _run_consolidate(sync_db, workspace_id, tmp_path, _baseline_e15a(("01-12", _CASA)))
    [imovel] = baseline["imoveis_consolidados"]
    with sync_db() as session:
        codigos = list(session.execute(select(PropertyIdentity.codigo_rfb)).scalars())
    assert imovel["codigo_rfb"] == "12"
    assert codigos == ["12"]
    assert all(re.fullmatch(r"\d{2}", c) and len(c) <= _LARGURA_DA_COLUNA for c in codigos)


def _e15c_entries(apto: str, casa: str) -> list[dict]:
    baseline = _baseline_e15a(("01-11", _APTO), ("12", _CASA))
    imoveis = consolidate_from_itens(baseline)["imoveis_consolidados"]
    for pid, imovel in zip((apto, casa), imoveis):
        imovel.update(property_id=pid, endereco_canonical="exemplo 100")
    return imoveis


# Os três leem a mesma policy: as entries do E1.5c (que viram supersessão durável,
# ADR-324), a projeção de excluídos do E5 e o sweep. `'01-11'` cru é genérico para o
# dedup, que o funde na casa — maior valor vence, e o outro imóvel some.
def test_os_tres_alimentadores_do_dedup_elegem_o_mesmo_vencedor(sync_db, workspace_id):
    from dev.backfill_property_supersession import _synthetic_entries

    apto = _seed(sync_db, workspace_id, "01-11", _APTO)
    casa = _seed(sync_db, workspace_id, "12", _CASA, minuto=1)
    with sync_db() as session:
        rows = list(session.execute(select(PropertyIdentity)).scalars())
    alimentadores = (
        _e15c_entries(apto, casa),
        _dedup_entries(rows, None),
        _synthetic_entries(rows, None),
    )
    vencedores = [resolve_dedup_winner_by_property_id(feed) for feed in alimentadores]
    assert vencedores == [{apto: apto, casa: casa}] * 3
