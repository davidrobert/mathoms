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
from dev.certify_ledger_local import (
    _e2_payloads_with_census,
    _e3_of_run,
    _persisted_e3_by_key,
)

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
    run = PipelineRun(
        id=str(uuid.uuid4()), workspace_id=ws, status="completed", completed_at=quando
    )
    session.add(run)
    session.flush()
    return run.id


def _seed_e2(session, ws: str, run_id: str, key: str, marca: str, quando: datetime) -> None:
    session.add(
        PipelineArtifact(
            workspace_id=ws,
            pipeline_run_id=run_id,
            stage="extract_statements",
            artifact_key=key,
            content_json={"marca": marca, "transacoes": []},
            created_at=quando,
        )
    )
    session.flush()


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
    monkeypatch.setattr(mod, "_e4_of_run", lambda _s, _w, _r: {})
    monkeypatch.setattr(
        mod,
        "_rederive",
        lambda _s, _w, _r: (_StoreComG1(), [], _FakeE3Result(), _FakeResult(), {}, {}),
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


# ─────────── corte temporal do E2 + censo de proveniência (ADR-421 D3) ───────────


@pytest.fixture
def e2_tres_proveniencias(sync_db):
    """E2 do próprio run, E2 herdado, e E2 nascido DEPOIS do fim do run."""
    with sync_db() as session:
        ws = _seed_workspace(session)
        run_velho = _seed_run(session, ws, _ANTIGO)
        run = _seed_run(session, ws, _NOVO)
        _seed_e2(session, ws, run, "k_run", "do-run", _NOVO - timedelta(hours=1))
        _seed_e2(session, ws, run_velho, "k_shared", "herdado", _ANTIGO)
        # Mesma key do herdado, escrita por um run POSTERIOR (o UNIQUE (run, stage, key)
        # do schema impede repetir a key no mesmo run). Sem o corte ela VENCE o
        # `_latest_by_canonical` e contamina o substrato com dado que o run não podia ler.
        run_futuro = _seed_run(session, ws, _NOVO + timedelta(days=2))
        _seed_e2(session, ws, run_futuro, "k_shared", "pos-run", _NOVO + timedelta(days=1))
        session.commit()
        yield session, ws, run


def test_corte_temporal_descarta_o_e2_nascido_depois_do_fim_do_run(e2_tres_proveniencias) -> None:
    """MUTAÇÃO 2 documentada: remover o corte temporal reprova AQUI."""
    session, ws, run = e2_tres_proveniencias
    payloads, _censo = _e2_payloads_with_census(session, ws, run)
    assert payloads[("extract_statements", "k_shared")]["marca"] == "herdado"


def test_censo_conta_do_run_herdado_e_descartado(e2_tres_proveniencias) -> None:
    session, ws, run = e2_tres_proveniencias
    _payloads, censo = _e2_payloads_with_census(session, ws, run)
    assert censo["do_run"] == 1
    assert censo["herdado"] == 1
    assert censo["descartado_pos_run"] == 1
    assert censo["corte"] == "aplicado"


def test_sem_completed_at_o_censo_declara_o_corte_indisponivel(sync_db) -> None:
    """D6: eixo sem insumo declara o motivo — nunca finge que o corte foi aplicado."""
    with sync_db() as session:
        ws = _seed_workspace(session)
        run = PipelineRun(id=str(uuid.uuid4()), workspace_id=ws, status="running")
        session.add(run)
        session.flush()
        _seed_e2(session, ws, run.id, "k1", "sem-corte", _NOVO)
        session.commit()
        _payloads, censo = _e2_payloads_with_census(session, ws, run.id)
        assert censo["corte"] == "indisponível (run sem completed_at)"
        assert censo["descartado_pos_run"] == 0


# ─────────── anti-amputação: eixo E4 vem do PUBLICADO (ADR-421 D4) ───────────

_DUPLICATA = [
    {"tipo": "CDB", "instituicao": "Banco X", "descricao": "CDB 2028", "valor_atual": 1000.0},
    {"tipo": "cdb", "instituicao": "banco x", "descricao": "CDB 2028", "valor_atual": 1000.0},
]


def _seed_e4(session, ws: str, run_id: str, key: str, payload: dict, quando: datetime) -> None:
    session.add(
        PipelineArtifact(
            workspace_id=ws,
            pipeline_run_id=run_id,
            stage="categorize_transactions",
            artifact_key=key,
            content_json=payload,
            created_at=quando,
        )
    )
    session.flush()


@pytest.fixture
def run_com_e4_publicado(sync_db):
    """Run cujo E4 PUBLICADO tem investimentos dupla-contados — a re-derivação, não."""
    with sync_db() as session:
        ws = _seed_workspace(session)
        run = _seed_run(session, ws, _NOVO)
        _seed_e4(session, ws, run, "investimentos", {"dados": _DUPLICATA}, _NOVO)
        _seed_e4(session, ws, run, "patrimonio", {"dados": {"imoveis": []}}, _NOVO)
        session.commit()
        yield session, ws, run


def _certify_com_e4_amputado(mod, monkeypatch, session, ws, run):
    """`certify` com re-derivação AMPUTADA — `investimentos` vazio, `patrimonio` ausente."""
    monkeypatch.setattr(mod, "_row_counts", lambda _s, _w: {"pipeline_artifacts": 0})
    monkeypatch.setattr(mod, "_blast_radius_or_empty", lambda _s, _w: {})
    monkeypatch.setattr(mod, "_persisted_e3_subject", lambda _s, _w, _r: {})
    monkeypatch.setattr(
        mod,
        "_rederive",
        lambda _s, _w, _r: (
            _StoreVazio(),
            [],
            _FakeE3Result(),
            _FakeResult(),
            {"investimentos": {"dados": []}},
            {},
        ),
    )
    return mod.certify(session, ws, run)


def test_colisao_de_investimento_vem_do_e4_publicado(run_com_e4_publicado, monkeypatch) -> None:
    """GATE anti-amputação: sobre a re-derivação o detector devolveria 0 sobre ZERO posições."""
    from dev import certify_ledger_local as mod

    session, ws, run = run_com_e4_publicado
    report = _certify_com_e4_amputado(mod, monkeypatch, session, ws, run)
    assert len(report.investment_collisions) == 1
    assert report.e4_subject == "entregue"


def test_patrimonio_do_publicado_nao_sai_como_balde_ausente(
    run_com_e4_publicado, monkeypatch
) -> None:
    from dev import certify_ledger_local as mod

    session, ws, run = run_com_e4_publicado
    report = _certify_com_e4_amputado(mod, monkeypatch, session, ws, run)
    unidades = {b.unit: b for b in report.e4_buckets}
    assert unidades["patrimonio"].detail != "balde ausente no sujeito"


def test_sem_e4_publicado_o_eixo_declara_que_e_sombra(dois_runs, monkeypatch) -> None:
    """D6: sem insumo no sujeito o rótulo diz `sombra` — nunca herda em silêncio."""
    from dev import certify_ledger_local as mod

    session, ws, run_a, _b = dois_runs
    report = _certify_com_e4_amputado(mod, monkeypatch, session, ws, run_a)
    assert report.e4_subject == "sombra"


class _StoreVazio:
    def list_keys(self, _stage):
        return []

    def read(self, _stage, _key):
        return {}


# ─────────── D5: predicado de certificar ≠ predicado de pontuar KR-B ───────────


def test_certificar_nao_exige_evidencia_de_enforce(run_com_e4_publicado, monkeypatch) -> None:
    """Sem a separação, tornar o entregue o default RECUSARIA 51 dos 61 runs (M15)."""
    # `evidence_from_retention` exige `removals_publicadas > 0`, e só 10 dos 61 runs têm
    # essa evidência. O run desta fixture não tem `PipelineStageLog` nenhum: se `certify`
    # passasse pelo predicado da KR-B, levantaria `EntregueRecusado`.
    from dev import certify_ledger_local as mod

    session, ws, run = run_com_e4_publicado
    report = _certify_com_e4_amputado(mod, monkeypatch, session, ws, run)
    assert report.e4_subject == "entregue"
    assert report.entregue == {}


def test_modo_entregue_segue_recusando_run_sem_enforce(run_com_e4_publicado) -> None:
    """O outro lado da separação: pontuar a KR-B continua fail-closed."""
    import pytest as _pytest

    from dev.certify_ledger_local import EntregueRecusado, certify_entregue

    session, ws, run = run_com_e4_publicado
    with _pytest.raises(EntregueRecusado):
        certify_entregue(session, ws, run)
