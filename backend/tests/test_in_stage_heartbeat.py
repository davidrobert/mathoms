"""A37.l12 (CTO-06) — heartbeat in-stage no loop de documentos.

Critério de aceite (fake clock via ``last_heartbeat_at`` retro-datado):
stage de 20 min COM batida in-stage → watchdog não flipa; SEM batida →
flipa (comportamento ADR-172 preservado para travas reais). Batida é DB
write CAS (``WHERE status='running'``) — nunca thread/timer (ADR-111),
nunca read-modify-write cross-worker (anti flip-flop).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from backend.app.core.database import _SQLITE_BUSY_TIMEOUT_MS as POOL_BUSY_TIMEOUT_MS
from backend.app.core.database import Base, _sqlite_connect_args, attach_sqlite_pragmas
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.pipeline.heartbeat import (
    _SQLITE_BUSY_TIMEOUT_MS as HEARTBEAT_BUSY_TIMEOUT_MS,
)
from backend.app.services.pipeline.heartbeat import record_in_stage_heartbeat
from backend.app.services.pipeline.pipeline_failure_reasons import HEARTBEAT_TIMEOUT
from backend.app.tasks.periodic_tasks import detect_stuck_runs
from backend.tests.factories.builders import make_user, make_workspace
from pipeline.live_progress import emit_item_progress


async def _make_run(
    db: AsyncSession,
    *,
    status: PipelineRunStatus = PipelineRunStatus.running,
    heartbeat_minutes_ago: int = 20,
) -> PipelineRun:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(
        workspace_id=ws.id,
        status=status,
        current_stage="extract_with_llm",
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        last_heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=heartbeat_minutes_ago),
    )
    db.add(run)
    await db.commit()
    return run


async def _reload(db: AsyncSession, run_id: str) -> PipelineRun:
    return (
        await db.execute(
            select(PipelineRun)
            .where(PipelineRun.id == run_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _emit_doc_progress(run_id: str, items_done: int, items_total: int = 8) -> None:
    emit_item_progress(
        run_id,
        "extract_with_llm",
        current_item=f"doc_{items_done}.pdf",
        items_done=items_done,
        items_total=items_total,
        phase="preparing",
    )


@pytest.fixture(autouse=True)
def _silence_publishes(monkeypatch):
    monkeypatch.setattr(
        "backend.app.tasks.periodic_tasks.publish_run_failed",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline.events.publish_item_progress",
        lambda *_a, **_k: None,
    )


@pytest.mark.asyncio
async def test_long_stage_with_in_stage_beats_survives_watchdog(db: AsyncSession) -> None:
    """Stage de 20 min COM batida in-stage no loop de docs → watchdog não flipa."""
    run = await _make_run(db, heartbeat_minutes_ago=20)
    before = datetime.now(timezone.utc)

    _emit_doc_progress(run.id, items_done=10)

    assert detect_stuck_runs.run()["detected"] == 0
    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.running
    assert refreshed.failure_reason is None
    assert _as_utc(refreshed.last_heartbeat_at) >= before


@pytest.mark.asyncio
async def test_long_stage_without_beats_flips(db: AsyncSession) -> None:
    """SEM batida in-stage o comportamento atual é preservado: trava real flipa."""
    run = await _make_run(db, heartbeat_minutes_ago=20)

    assert detect_stuck_runs.run()["detected"] == 1
    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.failed
    assert refreshed.failure_reason == HEARTBEAT_TIMEOUT


@pytest.mark.asyncio
async def test_heartbeat_cas_does_not_resurrect_flipped_run(db: AsyncSession) -> None:
    """Anti flip-flop: run já flipado pelo watchdog não renova heartbeat nem volta a running."""
    run = await _make_run(db, status=PipelineRunStatus.failed, heartbeat_minutes_ago=20)
    stale = run.last_heartbeat_at

    assert record_in_stage_heartbeat(run.id) is False

    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.failed
    assert _as_utc(refreshed.last_heartbeat_at) == _as_utc(stale)


@pytest.mark.asyncio
async def test_heartbeat_cas_updates_running_run(db: AsyncSession) -> None:
    run = await _make_run(db, heartbeat_minutes_ago=20)
    before = datetime.now(timezone.utc)

    assert record_in_stage_heartbeat(run.id) is True

    refreshed = await _reload(db, run.id)
    assert _as_utc(refreshed.last_heartbeat_at) >= before


@pytest.mark.asyncio
async def test_heartbeat_cadence_every_n_docs(db: AsyncSession, monkeypatch) -> None:
    """Env ``MATHOMS_HEARTBEAT_EVERY_N_DOCS=3`` → batida só em items_done múltiplo de 3."""
    monkeypatch.setenv("MATHOMS_HEARTBEAT_EVERY_N_DOCS", "3")
    beats: list[str] = []
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.record_in_stage_heartbeat",
        lambda run_id: beats.append(run_id) or True,
    )

    for items_done in range(6):
        _emit_doc_progress("run-cadence", items_done=items_done)

    assert len(beats) == 2  # items_done 0 e 3


@pytest.mark.asyncio
async def test_heartbeat_cadence_invalid_env_falls_back_to_default(
    db: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setenv("MATHOMS_HEARTBEAT_EVERY_N_DOCS", "not-a-number")
    beats: list[str] = []
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.record_in_stage_heartbeat",
        lambda run_id: beats.append(run_id) or True,
    )

    for items_done in range(11):
        _emit_doc_progress("run-fallback", items_done=items_done)

    assert len(beats) == 2  # default N=10: bate em items_done 0 e 10


@pytest.mark.asyncio
async def test_no_heartbeat_without_run_id(monkeypatch) -> None:
    """CLI/testes (``pipeline_run_id`` ausente) → no-op, sem DB write."""
    beats: list[str] = []
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.record_in_stage_heartbeat",
        lambda run_id: beats.append(run_id) or True,
    )

    emit_item_progress(
        None,
        "extract_with_llm",
        current_item="doc.pdf",
        items_done=0,
        items_total=1,
        phase="preparing",
    )

    assert beats == []


@pytest.mark.asyncio
async def test_heartbeat_fires_even_if_ws_publish_fails(db: AsyncSession, monkeypatch) -> None:
    """Batida não depende do publish WS — Redis fora não pode matar o heartbeat."""

    def _boom(*_a, **_k):
        raise RuntimeError("redis down")

    monkeypatch.setattr("backend.app.services.pipeline.events.publish_item_progress", _boom)
    run = await _make_run(db, heartbeat_minutes_ago=20)
    before = datetime.now(timezone.utc)

    _emit_doc_progress(run.id, items_done=0)

    refreshed = await _reload(db, run.id)
    assert _as_utc(refreshed.last_heartbeat_at) >= before


class _SqliteBind:
    class dialect:  # noqa: N801 — shape mínimo do bind SQLAlchemy
        name = "sqlite"


class _FakeConnection:
    def __init__(self, statements: list[str]):
        self._statements = statements

    def detach(self) -> None:
        self._statements.append("DETACH")


class _FakeSessionBase:
    def __init__(self, statements: list[str] | None = None):
        self._statements = [] if statements is None else statements

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get_bind(self):
        return _SqliteBind()

    def connection(self):
        return _FakeConnection(self._statements)


class _LockedSession(_FakeSessionBase):
    def execute(self, *args, **kwargs):
        raise OperationalError("stmt", None, Exception("database is locked"))

    def commit(self):
        raise AssertionError("commit não deve rodar sob lock")


class _SpySession(_FakeSessionBase):
    def execute(self, stmt, *args, **kwargs):
        self._statements.append(str(stmt))
        return type("_Result", (), {"rowcount": 1})()

    def commit(self):
        self._statements.append("COMMIT")


@pytest.mark.asyncio
async def test_heartbeat_lock_contention_returns_false_sem_propagar(monkeypatch) -> None:
    """Regressão do gate A37 (run 866a1885): lock do DB em dev vira ``False``
    best-effort — nunca propaga nem bloqueia o loop de documentos (as batidas
    bloqueavam 30s cada e estouraram o hard time limit de 3600s)."""
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.SyncSessionLocal",
        lambda: _LockedSession(),
    )
    assert record_in_stage_heartbeat("run-locked") is False


@pytest.mark.asyncio
async def test_heartbeat_sqlite_aplica_busy_timeout_curto(monkeypatch) -> None:
    """Em SQLite a batida configura busy_timeout curto ANTES do UPDATE — é o
    que garante o comportamento não-bloqueante sob write-lock da sessão do task.
    A conexão sai do pool ANTES do PRAGMA: exceção entre os dois não pode
    devolver ao pool a conexão de timeout curto."""
    statements: list[str] = []
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.SyncSessionLocal",
        lambda: _SpySession(statements),
    )
    assert record_in_stage_heartbeat("run-spy") is True
    assert statements[0] == "DETACH"
    assert "busy_timeout" in statements[1]
    assert statements[-1] == "COMMIT"


@pytest.fixture()
def pooled_sqlite_engine(tmp_path, monkeypatch) -> Iterator[Engine]:
    """SQLite em ARQUIVO + ``QueuePool`` default + pragmas de produção: o ``StaticPool`` do conftest entrega UMA conexão a todas as sessões e esconde o vazamento por construção."""
    url = f"sqlite:///{tmp_path / 'heartbeat_pool.db'}"
    engine = create_engine(url, connect_args=_sqlite_connect_args(url))
    attach_sqlite_pragmas(engine)
    assert isinstance(engine.pool, QueuePool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.SyncSessionLocal",
        sessionmaker(bind=engine, expire_on_commit=False),
    )
    yield engine
    engine.dispose()


def _seed_running_run(engine: Engine) -> str:
    with Session(engine) as session:
        user = User(email="heartbeat-pool@test.com", hashed_password="x", full_name="Pool")
        session.add(user)
        session.flush()
        workspace = Workspace(name="Heartbeat pool", owner_id=user.id)
        session.add(workspace)
        session.flush()
        run = PipelineRun(workspace_id=workspace.id, status=PipelineRunStatus.running)
        session.add(run)
        session.commit()
        return run.id


def _busy_timeouts_of_idle_pool_connections(engine: Engine) -> list[int]:
    """Sessões abertas em paralelo seguram conexões distintas: lê TODA conexão ociosa, seja qual for a ordem de checkout do pool."""
    sessions = [Session(engine) for _ in range(engine.pool.checkedin())]
    try:
        return [s.execute(text("PRAGMA busy_timeout")).scalar_one() for s in sessions]
    finally:
        for session in sessions:
            session.close()


def _busy_timeout_seen_by_heartbeat_update(engine: Engine) -> list[int]:
    seen: list[int] = []

    def _capture(_conn, cursor, statement, *_args) -> None:
        if statement.startswith("UPDATE pipeline_runs") and "last_heartbeat_at" in statement:
            seen.append(cursor.connection.execute("PRAGMA busy_timeout").fetchone()[0])

    event.listen(engine, "before_cursor_execute", _capture)
    return seen


def _assert_pool_keeps_production_busy_timeout(engine: Engine) -> None:
    timeouts = _busy_timeouts_of_idle_pool_connections(engine)
    assert timeouts, "pool sem conexão ociosa: a leitura seria vacuosa"
    assert timeouts == [POOL_BUSY_TIMEOUT_MS] * len(timeouts)


def test_heartbeat_nao_vaza_busy_timeout_curto_para_o_pool(pooled_sqlite_engine: Engine) -> None:
    """Regressão: o ``PRAGMA busy_timeout`` da batida é estado da conexão DBAPI e
    sobrevivia ao checkin no ``QueuePool`` — a sessão seguinte (artefato do stage,
    ``_record_stage_result``, ``LLMBudgetService``) esperava 200ms por lock, não 30s."""
    run_id = _seed_running_run(pooled_sqlite_engine)

    assert record_in_stage_heartbeat(run_id) is True

    _assert_pool_keeps_production_busy_timeout(pooled_sqlite_engine)


def test_heartbeat_sob_write_lock_falha_rapido_sem_vazar(pooled_sqlite_engine: Engine) -> None:
    """Contrato preservado: sob o write-lock de outra sessão o UPDATE da batida roda
    com o timeout curto e vira ``False`` — e a conexão curta não volta ao pool."""
    run_id = _seed_running_run(pooled_sqlite_engine)
    seen = _busy_timeout_seen_by_heartbeat_update(pooled_sqlite_engine)

    with Session(pooled_sqlite_engine) as holder:
        holder.execute(
            update(PipelineRun).where(PipelineRun.id == run_id).values(current_stage="lock")
        )
        assert record_in_stage_heartbeat(run_id) is False
        holder.rollback()

    assert seen == [HEARTBEAT_BUSY_TIMEOUT_MS]
    _assert_pool_keeps_production_busy_timeout(pooled_sqlite_engine)
