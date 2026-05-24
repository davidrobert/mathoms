"""ADR-267 regressão de _persist_llm_suggestions: soft-supersede + dedup_key + dismiss window + source isolation + normalização léxica."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.task import TaskSuggestion
from backend.app.models.user import User
from backend.app.models.workspace import Workspace


async def _build_engines(db_file):
    """Engines async + sync apontando para o mesmo SQLite file."""
    import backend.app.models  # noqa: F401
    from backend.app.core.database import Base

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    sync_engine = create_engine(f"sqlite:///{db_file}")
    async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    sync_session = sessionmaker(bind=sync_engine, expire_on_commit=False)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_session, sync_session


async def _create_user(session):
    from backend.app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email=f"adr266_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("pass"),
        full_name="ADR-267 Tester",
    )
    session.add(user)
    await session.flush()
    return user


async def _create_ws_and_run(session, user_id: str) -> tuple[str, str]:
    ws = Workspace(id=str(uuid.uuid4()), owner_id=user_id, name="ADR-267 WS")
    session.add(ws)
    await session.flush()
    run = PipelineRun(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        status=PipelineRunStatus.completed,
        total_documents=1,
    )
    session.add(run)
    await session.commit()
    return ws.id, run.id


async def _seed(async_session_factory):
    async with async_session_factory() as session:
        user = await _create_user(session)
        ws_id, run_id = await _create_ws_and_run(session, user.id)
        return {"ws_id": ws_id, "run_id": run_id}


async def _add_e5_artifact(async_session_factory, *, ws_id, run_id, tarefas):
    async with async_session_factory() as session:
        session.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage="E5",
                artifact_key="analise_financeira",
                content_json={"tarefas_sugeridas": tarefas},
            )
        )
        await session.commit()


async def _make_run(async_session_factory, *, ws_id: str) -> str:
    async with async_session_factory() as session:
        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws_id,
            status=PipelineRunStatus.completed,
            total_documents=1,
        )
        session.add(run)
        await session.commit()
        return run.id


@pytest_asyncio.fixture
async def env(tmp_path, monkeypatch):
    """Workspace + run completed + SyncSessionLocal patcheada para o mesmo SQLite."""
    import backend.app.tasks.pipeline_task as task_module

    db_file = tmp_path / "adr266.db"
    async_session, sync_session = await _build_engines(db_file)
    monkeypatch.setattr(task_module, "SyncSessionLocal", sync_session)
    seeded = await _seed(async_session)
    return {"async_session": async_session, "sync_session": sync_session, **seeded}


def _persist(ws_id, run_id, tmp_path):
    from backend.app.tasks.pipeline_task import _persist_llm_suggestions

    _persist_llm_suggestions(ws_id, run_id, tmp_path)


def _count(sync_session, ws_id, *, source="e5n_llm", status=None):
    with sync_session() as s:
        q = select(TaskSuggestion).where(
            TaskSuggestion.workspace_id == ws_id,
            TaskSuggestion.source == source,
        )
        if status is not None:
            q = q.where(TaskSuggestion.status == status)
        return len(s.execute(q).scalars().all())


async def _inject_and_persist(env, tarefas, *, run_id=None, tmp_path):
    """Adiciona artifact E5 + chama _persist_llm_suggestions. Usa run_id default do env."""
    rid = run_id or env["run_id"]
    await _add_e5_artifact(env["async_session"], ws_id=env["ws_id"], run_id=rid, tarefas=tarefas)
    _persist(env["ws_id"], rid, tmp_path)


def _flip_first_status(sync_session, ws_id, *, new_status, reviewed_at):
    with sync_session() as s:
        row = (
            s.execute(
                select(TaskSuggestion)
                .where(TaskSuggestion.workspace_id == ws_id)
                .order_by(TaskSuggestion.created_at)
            )
            .scalars()
            .first()
        )
        row.status = new_status
        row.reviewed_at = reviewed_at
        s.commit()


@pytest.mark.asyncio
async def test_idempotent_cross_run_keeps_pending_count(env, tmp_path):
    """Run 2× com mesmo artifact → mesma contagem pending; 0 supersedidas."""
    tarefas = [
        {"tarefa": "Revisar PGBL Bradesco", "categoria": "Investimentos"},
        {"tarefa": "Aumentar reserva", "categoria": "Reserva"},
    ]
    await _inject_and_persist(env, tarefas, tmp_path=tmp_path)
    assert _count(env["sync_session"], env["ws_id"], status="pending") == 2

    new_run = await _make_run(env["async_session"], ws_id=env["ws_id"])
    await _inject_and_persist(env, tarefas, run_id=new_run, tmp_path=tmp_path)

    assert _count(env["sync_session"], env["ws_id"], status="pending") == 2
    assert _count(env["sync_session"], env["ws_id"], status="superseded") == 0


@pytest.mark.asyncio
async def test_dismiss_window_blocks_recreation(env, tmp_path):
    """Rejected em <90d com mesmo dedup_key → run novo não recria."""
    tarefas = [{"tarefa": "Revisar PGBL", "categoria": "Investimentos"}]
    await _inject_and_persist(env, tarefas, tmp_path=tmp_path)
    _flip_first_status(
        env["sync_session"],
        env["ws_id"],
        new_status="rejected",
        reviewed_at=datetime.now(timezone.utc) - timedelta(days=10),
    )

    new_run = await _make_run(env["async_session"], ws_id=env["ws_id"])
    await _inject_and_persist(env, tarefas, run_id=new_run, tmp_path=tmp_path)

    assert _count(env["sync_session"], env["ws_id"], status="pending") == 0
    assert _count(env["sync_session"], env["ws_id"], status="rejected") == 1


_APPROVED_INITIAL = [
    {"tarefa": "Revisar PGBL", "categoria": "Investimentos"},
    {"tarefa": "Aumentar reserva", "categoria": "Reserva"},
]
_APPROVED_RERUN = [
    {"tarefa": "Aumentar reserva", "categoria": "Reserva"},
    {"tarefa": "Diversificar bonds", "categoria": "Investimentos"},
]


@pytest.mark.asyncio
async def test_approved_preserved_across_runs(env, tmp_path):
    """Approved nunca vira superseded — audit trail intacto."""
    await _inject_and_persist(env, _APPROVED_INITIAL, tmp_path=tmp_path)
    _flip_first_status(
        env["sync_session"],
        env["ws_id"],
        new_status="approved",
        reviewed_at=datetime.now(timezone.utc),
    )
    new_run = await _make_run(env["async_session"], ws_id=env["ws_id"])
    await _inject_and_persist(env, _APPROVED_RERUN, run_id=new_run, tmp_path=tmp_path)

    assert _count(env["sync_session"], env["ws_id"], status="approved") == 1
    assert _count(env["sync_session"], env["ws_id"], status="pending") == 2
    assert _count(env["sync_session"], env["ws_id"], status="superseded") == 0


def _add_manual_suggestion(sync_session, ws_id):
    with sync_session() as s:
        s.add(
            TaskSuggestion(
                id=str(uuid.uuid4()),
                workspace_id=ws_id,
                source="cross_validation",
                status="pending",
                dedup_key="manual-key-1",
                proposed_payload={"title": "Manual sugg", "category": "Other"},
            )
        )
        s.commit()


@pytest.mark.asyncio
async def test_other_source_untouched(env, tmp_path):
    """Suggestion source!='e5n_llm' fica intacta após run E5."""
    _add_manual_suggestion(env["sync_session"], env["ws_id"])
    await _inject_and_persist(env, [{"tarefa": "Algo LLM", "categoria": "X"}], tmp_path=tmp_path)

    cv_pending = _count(
        env["sync_session"], env["ws_id"], source="cross_validation", status="pending"
    )
    llm_pending = _count(env["sync_session"], env["ws_id"], source="e5n_llm", status="pending")
    assert cv_pending == 1
    assert llm_pending == 1


def test_normalize_collapses_lexical_variations():
    """Helper puro: variações léxicas idênticas semanticamente → mesma key."""
    from backend.app.services.task_suggestion_dedup import compute_task_suggestion_dedup_key

    a = compute_task_suggestion_dedup_key("e5n_llm", "Revisar PGBL Bradesco", "Investimentos")
    b = compute_task_suggestion_dedup_key("e5n_llm", "  REVISAR pgbl  bradesco ", "investimentos")
    c = compute_task_suggestion_dedup_key("e5n_llm", "Revisar\tPGBL\nBradesco", "Investimentos")
    assert a == b == c
    other_src = compute_task_suggestion_dedup_key(
        "cross_validation", "Revisar PGBL Bradesco", "Investimentos"
    )
    assert other_src != a
    other_cat = compute_task_suggestion_dedup_key("e5n_llm", "Revisar PGBL Bradesco", "Reserva")
    assert other_cat != a


@pytest.mark.asyncio
async def test_empty_drafts_is_noop(env, tmp_path):
    """Artifact sem tarefas_sugeridas (ou lista vazia) → nenhum write."""
    await _inject_and_persist(env, [], tmp_path=tmp_path)
    assert _count(env["sync_session"], env["ws_id"]) == 0

    new_run = await _make_run(env["async_session"], ws_id=env["ws_id"])
    _persist(env["ws_id"], new_run, tmp_path)
    assert _count(env["sync_session"], env["ws_id"]) == 0
