#!/usr/bin/env python3
"""Substrato do veredito é run-scoped — [[ADR-421]] D3 / conformidade à [[ADR-241]] (A42.l14).

O defeito mora na cláusula ``WHERE``: ``_persisted_e3_by_key`` é workspace-latest,
então certificar um run que não é o mais novo compara as keys dele contra artefato
de OUTRO run. Medido no dogfood: 60 dos 61 runs `completed` com E3. Por isso a
fixture é SQLite real — sessão fake não tem cláusula ``WHERE`` para errar, e seria
o mock/prod drift que a §Testes do CLAUDE.md proíbe.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PipelineArtifact, PipelineRun, User, Workspace
from dev.certify_ledger_local import _e3_of_run, _persisted_e3_by_key

_E3 = "reconcile_transactions"
_ANTIGO = datetime(2026, 5, 29, 12, 0, 0)
_NOVO = _ANTIGO + timedelta(days=63)


@pytest.fixture
def sync_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'run_scope.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _seed_workspace(session) -> str:
    """Materializa os pais da FK ([[ADR-371]]) — id sintético levantaria IntegrityError."""
    user = User(
        id=str(uuid.uuid4()),
        email=f"u-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        full_name="Test",
    )
    session.add(user)
    session.flush()
    ws = Workspace(id=str(uuid.uuid4()), name="WS", owner_id=user.id)
    session.add(ws)
    session.flush()
    return ws.id


def _seed_run(session, ws: str, quando: datetime) -> str:
    run = PipelineRun(id=str(uuid.uuid4()), workspace_id=ws, status="completed")
    session.add(run)
    session.flush()
    return run.id


def _seed_e3(session, ws: str, run_id: str, key: str, n_tx: int, quando: datetime) -> None:
    session.add(
        PipelineArtifact(
            workspace_id=ws,
            pipeline_run_id=run_id,
            stage=_E3,
            artifact_key=key,
            content_json={"transacoes_total": n_tx, "transacoes": []},
            created_at=quando,
        )
    )
    session.flush()


@pytest.fixture
def dois_runs(sync_db):
    """Run A (antigo) e run B (novo) escrevem a MESMA ``artifact_key`` com counts distintos."""
    with sync_db() as session:
        ws = _seed_workspace(session)
        run_a = _seed_run(session, ws, _ANTIGO)
        run_b = _seed_run(session, ws, _NOVO)
        _seed_e3(session, ws, run_a, "g1", 11, _ANTIGO)
        _seed_e3(session, ws, run_b, "g1", 22, _NOVO)
        session.commit()
        yield session, ws, run_a, run_b


def test_e3_do_run_a_traz_os_grupos_de_a_e_nao_os_de_b(dois_runs) -> None:
    session, ws, run_a, _run_b = dois_runs
    assert _e3_of_run(session, ws, run_a)["g1"]["transacoes_total"] == 11


def test_e3_do_run_b_traz_os_grupos_de_b(dois_runs) -> None:
    session, ws, _run_a, run_b = dois_runs
    assert _e3_of_run(session, ws, run_b)["g1"]["transacoes_total"] == 22


def test_workspace_latest_e_o_substrato_ERRADO_para_run_nao_mais_recente(dois_runs) -> None:
    """MUTAÇÃO 1 documentada: reintroduzir workspace-latest como substrato reprova."""
    # FIXA o comportamento de `_persisted_e3_by_key`: devolve o run mais novo qualquer que
    # seja o run pedido. Não é bug do leitor (é o bloco de acreção de workspace da D1) — é
    # prova de que ele não serve de SUBSTRATO do veredito.
    session, ws, _run_a, _run_b = dois_runs
    assert _persisted_e3_by_key(session, ws)["g1"]["transacoes_total"] == 22


def test_certify_usa_o_e3_do_run_pinado_e_nao_o_workspace_latest(dois_runs, monkeypatch) -> None:
    """GATE: o drift de um run não-mais-recente não pode citar artefato de outro run."""
    # Antes do fix, `certify` passava `_persisted_e3_by_key` a `build_report`: certificar o
    # run A comparava as keys de A contra o E3 de B, e o count divergia (11 vs 22) por
    # construção do INSTRUMENTO, não do corpus.
    from dev import certify_ledger_local as mod

    session, ws, run_a, _run_b = dois_runs
    monkeypatch.setattr(mod, "_row_counts", lambda _s, _w: {"pipeline_artifacts": 0})
    monkeypatch.setattr(mod, "_blast_radius_or_empty", lambda _s, _w: {})
    monkeypatch.setattr(
        mod,
        "_rederive",
        lambda _s, _w, _r: (_StoreComG1(), [], _FakeE3Result(), _FakeResult(), {}),
    )
    report = mod.certify(session, ws, run_a)
    assert report.drift.count_diff == []
    assert report.drift.matched == 1


class _StoreComG1:
    """Store re-derivado que reproduz ``g1`` com o count do run A."""

    def list_keys(self, _stage):
        return ["g1"]

    def read(self, _stage, _key):
        return {"transacoes_total": 11, "transacoes": []}


class _FakeE3Result:
    statements_loaded = 1
    statements_reconciled = 1
    skipped_inputs = 0
    artifacts_written = 1


class _FakeResult:
    classified: list = []

    class cash_flow:
        transferencias_count = 0
