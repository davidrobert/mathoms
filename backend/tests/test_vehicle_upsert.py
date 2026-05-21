"""A18 L1 P4 (ADR-239 D1+D4) — upsert vehicles com identidade imutável."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.core.database import Base
from backend.app.models import (  # noqa: F401
    User,
    Vehicle,  # noqa: F401 — registra schema no metadata
    Workspace,
)
from backend.app.services.vehicle_upsert import (
    UpsertOutcome,
    upsert_vehicle_from_payload,
)


@pytest.fixture
def sync_db() -> Session:
    """SQLite em memória; create_all monta todas as tabelas (vehicles incluído)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def workspace_id(sync_db: Session) -> str:
    """Cria User + Workspace mínimos. Retorna workspace_id."""
    from backend.app.core.security import hash_password

    user = User(email="upsert@test.com", hashed_password=hash_password("p"), full_name="U")
    sync_db.add(user)
    sync_db.flush()
    ws = Workspace(name="WS-U", owner_id=user.id)
    sync_db.add(ws)
    sync_db.flush()
    return ws.id


def _payload(
    *, placa: str = "ABC1D23", renavam: str = "12345678900", cor: str | None = "preta"
) -> dict:
    return {
        "placa": placa,
        "renavam": renavam,
        "marca": "Yamaha",
        "modelo": "NMAX 160",
        "ano_modelo": 2024,
        "ano_fabricacao": 2024,
        "cor": cor,
        "combustivel": "gasolina",
        "exercicio": 2026,
        "categoria": "particular",
        "confidence": 0.95,
        "prompt_version": "crlv-v1.0.0",
    }


def test_insert_novo_vehicle(sync_db: Session, workspace_id: str):
    result = upsert_vehicle_from_payload(workspace_id, _payload(), db=sync_db)
    assert result.outcome is UpsertOutcome.inserted
    assert result.vehicle is not None
    assert result.vehicle.placa == "ABC1D23"
    assert result.vehicle.renavam == "12345678900"


def test_upsert_idempotente_mesma_placa_renavam(sync_db: Session, workspace_id: str):
    """Mesmo CRLV uploaded 2× → 2ª chamada updated (sem mudança em campos editáveis)."""
    r1 = upsert_vehicle_from_payload(workspace_id, _payload(), db=sync_db)
    r2 = upsert_vehicle_from_payload(workspace_id, _payload(), db=sync_db)
    assert r1.outcome is UpsertOutcome.inserted
    assert r2.outcome is UpsertOutcome.updated
    assert r2.vehicle.id == r1.vehicle.id  # mesma row


def test_atualiza_campos_editaveis(sync_db: Session, workspace_id: str):
    """ADR-239 D1: cor/combustível atualizam; identidade (placa, renavam, marca) NÃO."""
    r1 = upsert_vehicle_from_payload(workspace_id, _payload(cor="preta"), db=sync_db)
    r2 = upsert_vehicle_from_payload(workspace_id, _payload(cor="branca"), db=sync_db)
    assert r2.outcome is UpsertOutcome.updated
    assert r2.vehicle.cor == "branca"
    assert r2.vehicle.id == r1.vehicle.id


def test_mismatch_placa_renavam_dispara_needs_review(sync_db: Session, workspace_id: str):
    """ADR-239 D1: colisão (mesma placa, RENAVAM diferente) → identidade comprometida."""
    r1 = upsert_vehicle_from_payload(workspace_id, _payload(renavam="11111111111"), db=sync_db)
    assert r1.outcome is UpsertOutcome.inserted
    r2 = upsert_vehicle_from_payload(workspace_id, _payload(renavam="22222222222"), db=sync_db)
    assert r2.outcome is UpsertOutcome.needs_review
    assert r2.reason is not None and "RENAVAM" in r2.reason
    # Row original preservada — não sobrescrita.
    assert r2.vehicle.renavam == "11111111111"


def test_normaliza_placa_no_upsert(sync_db: Session, workspace_id: str):
    """Placa com hífen/lowercase é normalizada antes do upsert (idempotência)."""
    r1 = upsert_vehicle_from_payload(workspace_id, _payload(placa="abc-1234"), db=sync_db)
    r2 = upsert_vehicle_from_payload(workspace_id, _payload(placa="ABC1234"), db=sync_db)
    assert r1.outcome is UpsertOutcome.inserted
    assert r2.outcome is UpsertOutcome.updated  # mesma placa após normalização
    assert r1.vehicle.placa == "ABC1234"


def test_payload_sem_placa_dispara_needs_review(sync_db: Session, workspace_id: str):
    bad = _payload()
    bad["placa"] = ""
    r = upsert_vehicle_from_payload(workspace_id, bad, db=sync_db)
    assert r.outcome is UpsertOutcome.needs_review
    assert r.vehicle is None
