"""A18 L1 P4 parte 3 (ADR-239 D3+D4) — runner backend de reconciliação fuzzy."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.core.database import Base
from backend.app.models import (  # noqa: F401
    User,
    Vehicle,
    Workspace,
)
from backend.app.services.vehicle_reconciliation_runner import (
    reconcile_baseline_with_db,
)


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

    user = User(email="recon@test.com", hashed_password=hash_password("p"), full_name="U")
    sync_db.add(user)
    sync_db.flush()
    ws = Workspace(name="WS-R", owner_id=user.id)
    sync_db.add(ws)
    sync_db.flush()
    return ws.id


def _add_vehicle(db: Session, workspace_id: str, **kw) -> Vehicle:
    defaults = dict(placa="ABC1D23", renavam="12345678900", marca="Yamaha", modelo="NMAX 160")
    defaults.update(kw)
    ano = defaults.pop("ano", 2024)
    v = Vehicle(workspace_id=workspace_id, ano_modelo=ano, ano_fabricacao=ano, **defaults)
    db.add(v)
    db.flush()
    return v


def test_match_auto_merge_acima_de_threshold(sync_db: Session, workspace_id: str):
    """Descricao IRPF G02 bate forte com marca+modelo do vehicle → auto_merge."""
    v = _add_vehicle(sync_db, workspace_id, marca="Yamaha", modelo="NMAX 160", ano=2024)
    baseline = {
        "veiculos_consolidados": [{"descricao": "Yamaha NMAX 160 2024", "proprietario": "titular"}]
    }
    new_baseline, summary = reconcile_baseline_with_db(workspace_id, baseline, db=sync_db)
    assert summary.matched_count == 1
    assert new_baseline["veiculos_consolidados"][0]["veiculo_id"] == v.id


def test_no_candidate_sem_vehicles(sync_db: Session, workspace_id: str):
    """Workspace sem vehicles → entry baseline fica com veiculo_id=None, no_candidate."""
    baseline = {
        "veiculos_consolidados": [{"descricao": "Fiat Toro 2022", "proprietario": "titular"}]
    }
    new_baseline, summary = reconcile_baseline_with_db(workspace_id, baseline, db=sync_db)
    assert summary.no_candidate_count == 1
    assert new_baseline["veiculos_consolidados"][0]["veiculo_id"] is None


def test_baseline_sem_veiculos_e_sem_vehicles_no_db(sync_db: Session, workspace_id: str):
    """Curto-circuito: nada para reconciliar, total_items == 0."""
    baseline = {"veiculos_consolidados": []}
    new_baseline, summary = reconcile_baseline_with_db(workspace_id, baseline, db=sync_db)
    assert summary.total_items == 0
    assert new_baseline["veiculos_consolidados"] == []


def _make_other_workspace(db: Session) -> str:
    from backend.app.core.security import hash_password

    u = User(email="other@test.com", hashed_password=hash_password("p"), full_name="O")
    db.add(u)
    db.flush()
    ws = Workspace(name="WS-OTHER", owner_id=u.id)
    db.add(ws)
    db.flush()
    return ws.id


def test_isolation_cross_workspace(sync_db: Session, workspace_id: str):
    """Vehicle de outro workspace NÃO entra como candidato."""
    other_ws_id = _make_other_workspace(sync_db)
    _add_vehicle(sync_db, other_ws_id)
    baseline = {
        "veiculos_consolidados": [{"descricao": "Yamaha NMAX 160 2024", "proprietario": "titular"}]
    }
    new_baseline, summary = reconcile_baseline_with_db(workspace_id, baseline, db=sync_db)
    assert summary.no_candidate_count == 1
    assert new_baseline["veiculos_consolidados"][0]["veiculo_id"] is None


def test_archived_vehicle_nao_eh_candidato(sync_db: Session, workspace_id: str):
    """ADR-239 D1 — vehicle archived (archived_at not null) sai do pool."""
    from datetime import datetime, timezone

    v = _add_vehicle(sync_db, workspace_id, marca="Yamaha", modelo="NMAX 160", ano=2024)
    v.archived_at = datetime.now(timezone.utc)
    sync_db.flush()

    baseline = {
        "veiculos_consolidados": [{"descricao": "Yamaha NMAX 160 2024", "proprietario": "titular"}]
    }
    _, summary = reconcile_baseline_with_db(workspace_id, baseline, db=sync_db)
    assert summary.no_candidate_count == 1


def test_idempotente_fk_existente_e_valida(sync_db: Session, workspace_id: str):
    """Re-run: baseline já tem veiculo_id válida → skip (idempotent_skip)."""
    v = _add_vehicle(sync_db, workspace_id, marca="Yamaha", modelo="NMAX 160", ano=2024)
    baseline = {
        "veiculos_consolidados": [
            {
                "descricao": "Yamaha NMAX 160 2024",
                "proprietario": "titular",
                "veiculo_id": v.id,  # já reconciliado
            }
        ]
    }
    new_baseline, summary = reconcile_baseline_with_db(workspace_id, baseline, db=sync_db)
    # matched_count exclui idempotent_skip da contagem (summarize convention)
    assert summary.matched_count == 0
    assert summary.total_items == 1
    assert new_baseline["veiculos_consolidados"][0]["veiculo_id"] == v.id


def test_fk_stale_eh_limpada(sync_db: Session, workspace_id: str):
    """veiculo_id apontando para row inexistente → limpa e re-reconcilia."""
    _add_vehicle(sync_db, workspace_id, marca="Yamaha", modelo="NMAX 160", ano=2024)
    baseline = {
        "veiculos_consolidados": [
            {
                "descricao": "Yamaha NMAX 160 2024",
                "proprietario": "titular",
                "veiculo_id": "00000000-0000-0000-0000-000000000000",  # fake/stale
            }
        ]
    }
    new_baseline, summary = reconcile_baseline_with_db(workspace_id, baseline, db=sync_db)
    # Re-reconciliou contra vehicle real → matched_count=1.
    assert summary.matched_count == 1
    assert new_baseline["veiculos_consolidados"][0]["veiculo_id"] is not None
    assert (
        new_baseline["veiculos_consolidados"][0]["veiculo_id"]
        != "00000000-0000-0000-0000-000000000000"
    )
