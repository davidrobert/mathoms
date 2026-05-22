"""A18 L2 P4 (ADR-239 D3) — runner backend de reconciliação apolice."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.core.database import Base
from backend.app.models import (  # noqa: F401
    PropertyIdentity,
    User,
    Vehicle,
    Workspace,
)
from backend.app.services.apolice_reconciliation_runner import reconcile_apolice_with_db


@pytest.fixture
def sync_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def workspace_id(sync_db: Session) -> str:
    from backend.app.core.security import hash_password

    user = User(email="apol@test.com", hashed_password=hash_password("p"), full_name="U")
    sync_db.add(user)
    sync_db.flush()
    ws = Workspace(name="WS-AP", owner_id=user.id)
    sync_db.add(ws)
    sync_db.flush()
    return ws.id


def _add_vehicle(db: Session, workspace_id: str, *, placa="ABC1D23") -> Vehicle:
    v = Vehicle(
        workspace_id=workspace_id,
        placa=placa,
        renavam="12345678900",
        marca="YAMAHA",
        modelo="NMAX",
        ano_modelo=2024,
        ano_fabricacao=2024,
    )
    db.add(v)
    db.flush()
    return v


def _add_property(
    db: Session,
    workspace_id: str,
    *,
    titular_key="david",
    codigo_rfb="11",
    endereco="rua test 100 sao paulo sp",
    first_seen_year=2024,
) -> PropertyIdentity:
    p = PropertyIdentity(
        workspace_id=workspace_id,
        titular_key=titular_key,
        codigo_rfb=codigo_rfb,
        endereco_canonical=endereco,
        first_seen_year=first_seen_year,
    )
    db.add(p)
    db.flush()
    return p


def _apolice_combinada(placa: str, endereco_struct: dict) -> dict:
    return {
        "apolice_numero": "AP-1",
        "bens_segurados": [
            {"tipo": "veiculo", "placa": placa},
            {"tipo": "imovel", "endereco": endereco_struct},
        ],
    }


def test_reconciliacao_combinada_preenche_ambos_ids(sync_db: Session, workspace_id: str):
    v = _add_vehicle(sync_db, workspace_id, placa="XYZ9A87")
    p = _add_property(sync_db, workspace_id, endereco="rua tasso 61 rio rj")
    payload = _apolice_combinada(
        "XYZ9A87",
        {"logradouro": "Rua Tasso", "numero": "61", "cidade": "Rio", "uf": "RJ"},
    )
    new_payload, summary = reconcile_apolice_with_db(workspace_id, payload, db=sync_db)
    assert summary.matched == 2
    assert new_payload["bens_segurados"][0]["veiculo_id"] == v.id
    assert new_payload["bens_segurados"][1]["imovel_id"] == p.id


def test_no_candidate_sem_vehicles_e_sem_properties(sync_db: Session, workspace_id: str):
    payload = _apolice_combinada(
        "ABC1D23", {"logradouro": "X", "numero": "1", "cidade": "Y", "uf": "SP"}
    )
    new_payload, summary = reconcile_apolice_with_db(workspace_id, payload, db=sync_db)
    assert summary.no_candidate == 2
    assert new_payload["bens_segurados"][0].get("veiculo_id") is None
    assert new_payload["bens_segurados"][1].get("imovel_id") is None


def test_idempotente_fk_veiculo_existente_valida(sync_db: Session, workspace_id: str):
    v = _add_vehicle(sync_db, workspace_id, placa="ABC1D23")
    payload = {
        "apolice_numero": "AP-1",
        "bens_segurados": [{"tipo": "veiculo", "placa": "ABC1D23", "veiculo_id": v.id}],
    }
    new_payload, summary = reconcile_apolice_with_db(workspace_id, payload, db=sync_db)
    assert summary.idempotent_skip == 1
    assert summary.matched == 0
    assert new_payload["bens_segurados"][0]["veiculo_id"] == v.id


def test_fk_stale_eh_re_reconciliada(sync_db: Session, workspace_id: str):
    v = _add_vehicle(sync_db, workspace_id, placa="ABC1D23")
    payload = {
        "apolice_numero": "AP-1",
        "bens_segurados": [
            {
                "tipo": "veiculo",
                "placa": "ABC1D23",
                "veiculo_id": "00000000-0000-0000-0000-000000000000",
            }
        ],
    }
    new_payload, summary = reconcile_apolice_with_db(workspace_id, payload, db=sync_db)
    # FK stale limpa + re-match contra v existente → matched.
    assert summary.matched == 1
    assert new_payload["bens_segurados"][0]["veiculo_id"] == v.id


def test_isolation_cross_workspace(sync_db: Session, workspace_id: str):
    """Vehicle de outro workspace NÃO entra como candidato."""
    from backend.app.core.security import hash_password

    other_u = User(email="o@t.com", hashed_password=hash_password("p"), full_name="O")
    sync_db.add(other_u)
    sync_db.flush()
    other_ws = Workspace(name="WS-O", owner_id=other_u.id)
    sync_db.add(other_ws)
    sync_db.flush()
    _add_vehicle(sync_db, other_ws.id, placa="ABC1D23")
    payload = {"bens_segurados": [{"tipo": "veiculo", "placa": "ABC1D23"}]}
    new_payload, summary = reconcile_apolice_with_db(workspace_id, payload, db=sync_db)
    assert summary.no_candidate == 1
    assert new_payload["bens_segurados"][0].get("veiculo_id") is None


def test_apolice_vazia_curto_circuito(sync_db: Session, workspace_id: str):
    payload = {"apolice_numero": "AP-1", "bens_segurados": []}
    new_payload, summary = reconcile_apolice_with_db(workspace_id, payload, db=sync_db)
    assert summary.total_bens == 0
    assert new_payload == payload
