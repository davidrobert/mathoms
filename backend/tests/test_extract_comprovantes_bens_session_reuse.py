"""Regressão prod 2026-05-22 — stage reusa session do artifact_store em vez de abrir SyncSessionLocal paralela (`database is locked` em INSERT INTO vehicles após busy_timeout 30s; mesmo pattern do fix em DBPropertyIdentityResolver, 2026-05-18)."""

from __future__ import annotations

import inspect
import uuid
from pathlib import Path
from unittest.mock import patch

# Fernet key + MATHOMS_WORKSPACE_ROOT vêm de backend/tests/conftest.py.
from pipeline.stages import extract_comprovantes_bens as stage


def _make_engine_and_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import backend.app.models  # noqa: F401 — popula metadata
    from backend.app.core.database import Base, attach_sqlite_pragmas

    engine = create_engine("sqlite:///:memory:", future=True)
    attach_sqlite_pragmas(engine)
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine, future=True)
    return SL, SL()


def _seed_workspace(session):
    from backend.app.models import User, Workspace

    uid, wid = str(uuid.uuid4()), str(uuid.uuid4())
    session.add(
        User(
            id=uid,
            email=f"comprov-{uuid.uuid4().hex[:8]}@t.co",
            hashed_password="x",
            full_name="T",
        )
    )
    session.add(Workspace(id=wid, name="WS", owner_id=uid))
    session.commit()
    return wid


def _make_db_fixtures():
    SL, session = _make_engine_and_session()
    return SL, session, _seed_workspace(session)


def _crlv_payload(placa: str, renavam: str = "00000000001") -> dict:
    # Schema strict (crlv.schema.json) exige categoria; placa segue Mercosul.
    return {
        "placa": placa,
        "renavam": renavam,
        "marca": "YAMAHA",
        "modelo": "NMAX",
        "ano_modelo": 2018,
        "ano_fabricacao": 2018,
        "cor": "PRETA",
        "combustivel": "gasolina",
        "exercicio": 2024,
        "categoria": "particular",
        "confidence": 0.95,
        "prompt_version": "v1",
        "proprietario_cpf_masked": "***.123.456-**",
    }


def _make_fake_result():
    return type("R", (), {"tokens_in": 10, "tokens_out": 20, "cost_estimate_usd": 0.0})()


def _make_store(session, ws_id):
    from backend.app.services.db_artifact_store import DBArtifactStore

    return DBArtifactStore(session, workspace_id=ws_id, pipeline_run_id=str(uuid.uuid4()))


class _FakeCtx:
    def __init__(self, store):
        self._store = store

    def get_artifact_store(self):
        return self._store


def test_upsert_in_db_requires_db_kwarg():
    """Assinatura ``(ws_id, payload, *, db)`` — quebra se alguém reintroduzir SyncSessionLocal paralela."""
    sig = inspect.signature(stage._upsert_in_db)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["ws_id", "payload", "db"]
    assert params[2].kind is inspect.Parameter.KEYWORD_ONLY


def test_persist_processed_crlv_reuses_store_session():
    """`_persist_processed` (tipo=crlv) passa `store.session` ao upsert."""
    _, session, ws_id = _make_db_fixtures()
    store = _make_store(session, ws_id)
    ctx = _FakeCtx(store)
    payload = _crlv_payload("DAV0J51")

    with patch.object(stage, "_upsert_in_db", wraps=stage._upsert_in_db) as spy:
        summary = stage._persist_processed(
            Path("crlv_DAV0J51.pdf"), payload, _make_fake_result(), ctx, ws_id, "crlv"
        )

    assert spy.call_count == 1
    _, kwargs = spy.call_args
    assert kwargs["db"] is store.session
    assert summary["upsert_outcome"] == "inserted"
    session.close()


def _process_two_crlvs(stage_mod, ctx, ws_id):
    for placa, renavam in [("DAV0J51", "00143226094"), ("DAV0J52", "00143226095")]:
        stage_mod._persist_processed(
            Path(f"crlv_{placa}.pdf"),
            _crlv_payload(placa, renavam),
            _make_fake_result(),
            ctx,
            ws_id,
            "crlv",
        )


def test_two_crlvs_back_to_back_share_single_session():
    """Cenário do incidente prod: 2 docs CRLV → 1 session, sem `OperationalError`."""
    from backend.app.core import database as _db_mod
    from backend.app.models.vehicle import Vehicle

    SL, session, ws_id = _make_db_fixtures()
    ctx = _FakeCtx(_make_store(session, ws_id))

    with patch.object(_db_mod, "SyncSessionLocal", wraps=_db_mod.SyncSessionLocal) as spy:
        _process_two_crlvs(stage, ctx, ws_id)

    assert spy.call_count == 0, "stage não deve abrir SyncSessionLocal paralela"
    session.commit()
    parallel = SL()
    rows = parallel.query(Vehicle).filter_by(workspace_id=ws_id).all()
    assert sorted(v.placa for v in rows) == ["DAV0J51", "DAV0J52"]
    parallel.close()
    session.close()
