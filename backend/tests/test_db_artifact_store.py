"""Tests — ``backend.app.services.db_artifact_store.DBArtifactStore`` (Fase 2.1).

Valida:
- Round-trip write/read preserva dados exatos.
- ``list_keys`` cross-run (distinct artifact_key por workspace+stage).
- ``write`` é upsert (mesma key mesma run → UPDATE, não INSERT).
- ``delete_stage`` remove apenas artefatos da run atual.
- Sessão é injetada (store não cria/fecha sessão).
- Satisfaz os protocolos ``ArtifactStore`` e ``ReadableArtifactStore``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import (
    PipelineArtifact,
    PipelineRun,
    PipelineRunStatus,
    User,
    Workspace,
)
from backend.app.services.db_artifact_store import DBArtifactStore
from pipeline.artifact_store import ArtifactStore, ReadableArtifactStore


async def _seed_ws_and_run(db: AsyncSession, *, email: str = "st@test.com"):
    user = User(email=email, hashed_password=hash_password("p"), full_name="U")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    await db.flush()
    run = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.running)
    db.add(run)
    await db.flush()
    return ws.id, run.id


def _store_on_sync_conn(sync_session, *, workspace_id, pipeline_run_id):
    """Retorna ``DBArtifactStore`` para uso em run_sync."""
    return DBArtifactStore(
        sync_session,
        workspace_id=workspace_id,
        pipeline_run_id=pipeline_run_id,
    )


@pytest.mark.asyncio
async def test_write_then_read(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E2-extratos", "itau_202601", {"tx": [{"v": 1}]})
            s.commit()
            s2 = Session(sync_conn)
            store2 = _store_on_sync_conn(s2, workspace_id=ws_id, pipeline_run_id=run_id)
            return store2.read("E2-extratos", "itau_202601")

    raw = await db.connection()
    got = await raw.run_sync(_do)
    assert got == {"tx": [{"v": 1}]}


@pytest.mark.asyncio
async def test_write_is_upsert(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E3", "k", {"v": 1})
            store.write("E3", "k", {"v": 2})
            s.commit()

    raw = await db.connection()
    await raw.run_sync(_do)
    rows = (
        (
            await db.execute(
                select(PipelineArtifact).where(
                    PipelineArtifact.pipeline_run_id == run_id,
                    PipelineArtifact.stage == "E3",
                    PipelineArtifact.artifact_key == "k",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].content_json == {"v": 2}


@pytest.mark.asyncio
async def test_list_keys_and_exists(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E4", "receitas", {})
            store.write("E4", "despesas", {})
            store.write("E5", "analise", {})
            s.commit()
            return store.list_keys("E4"), store.exists("E4", "despesas"), store.exists("E4", "nope")

    raw = await db.connection()
    keys, exists_yes, exists_no = await raw.run_sync(_do)
    assert keys == ["despesas", "receitas"]
    assert exists_yes is True
    assert exists_no is False


@pytest.mark.asyncio
async def test_delete_and_delete_stage(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E3", "a", {})
            store.write("E3", "b", {})
            store.write("E4", "c", {})
            s.commit()
            store.delete("E3", "a")
            s.commit()
            remaining_e3 = store.list_keys("E3")
            removed = store.delete_stage("E3")
            s.commit()
            return remaining_e3, removed, store.list_keys("E3"), store.list_keys("E4")

    raw = await db.connection()
    remaining, removed, after_stage_del, e4 = await raw.run_sync(_do)
    assert remaining == ["b"]
    assert removed == 1
    assert after_stage_del == []
    assert e4 == ["c"]


@pytest.mark.asyncio
async def test_delete_stage_scoped_to_current_run(db: AsyncSession):
    """``delete_stage`` não apaga artefatos de outras runs."""
    ws_id, run_id = await _seed_ws_and_run(db, email="multi@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            other_run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
            s.add(other_run)
            s.flush()
            other_id = other_run.id

            store1 = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store2 = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=other_id)
            store1.write("E3", "x", {"run": 1})
            store2.write("E3", "x", {"run": 2})
            s.commit()
            removed = store1.delete_stage("E3")
            s.commit()
            # run atual limpo; outra run intocada
            return removed, store1.list_keys("E3"), store2.read("E3", "x")

    raw = await db.connection()
    removed, after, other_run_value = await raw.run_sync(_do)
    # list_keys retorna distinct no workspace — a outra run ainda tem "x"
    assert removed == 1
    assert after == ["x"]
    assert other_run_value == {"run": 2}


@pytest.mark.asyncio
async def test_satisfies_artifact_store_protocol(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db, email="proto@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            return isinstance(store, ArtifactStore), isinstance(store, ReadableArtifactStore)

    raw = await db.connection()
    is_full, is_read = await raw.run_sync(_do)
    assert is_full
    assert is_read


@pytest.mark.asyncio
async def test_store_does_not_close_session(db: AsyncSession):
    """Sessão injetada permanece utilizável pelo chamador após o store agir."""
    ws_id, run_id = await _seed_ws_and_run(db, email="noclose@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        s = Session(sync_conn)
        try:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E5", "analise", {"a": 1})
            s.commit()
            # A sessão ainda deve ser usável
            count = s.query(PipelineArtifact).filter_by(pipeline_run_id=run_id, stage="E5").count()
            return count
        finally:
            s.close()

    raw = await db.connection()
    n = await raw.run_sync(_do)
    assert n == 1
