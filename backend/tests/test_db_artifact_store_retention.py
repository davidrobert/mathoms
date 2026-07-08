"""Write-path de retenção (A33.l6 · W6-T05): nova versão do grupo
(workspace, stage-alias, artifact_key) marca as anteriores com
``retention_until``; a corrente fica NULL permanente (fail-safe); overwrite
no mesmo run (UPDATE) não marca; prazo já atribuído nunca é estendido."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import PipelineArtifact, PipelineRun, PipelineRunStatus, User, Workspace
from backend.app.services.storage.artifact_retention import ArtifactRetentionPolicy
from backend.app.services.storage.db_artifact_store import DBArtifactStore

_POLICY = ArtifactRetentionPolicy(superseded_days=30)


async def _seed_ws_and_run(db: AsyncSession, *, email: str):
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


def _store(s, *, workspace_id: str, pipeline_run_id: str) -> DBArtifactStore:
    return DBArtifactStore(
        s,
        workspace_id=workspace_id,
        pipeline_run_id=pipeline_run_id,
        retention_policy=_POLICY,
    )


def _new_run(s, ws_id: str) -> str:
    run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
    s.add(run)
    s.flush()
    return run.id


def _retention_by_run(s, ws_id: str) -> dict[str, Optional[datetime]]:
    rows = (
        s.query(PipelineArtifact.pipeline_run_id, PipelineArtifact.retention_until)
        .filter(PipelineArtifact.workspace_id == ws_id)
        .all()
    )
    return {r[0]: r[1] for r in rows}


def _assert_close_to_days_from_now(value: Optional[datetime] = None, *, days: int = 30) -> None:
    assert value is not None
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    assert (
        now + timedelta(days=days - 1) < aware < now + timedelta(days=days + 1)
    ), f"expected retention ~{days}d from now, got {aware.isoformat()}"


@pytest.mark.asyncio
async def test_new_version_marks_previous_superseded_current_stays_null(db: AsyncSession):
    ws_id, run_a = await _seed_ws_and_run(db, email="ret-basic@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            _store(s, workspace_id=ws_id, pipeline_run_id=run_a).write("E5", "analise", {"v": 1})
            s.commit()
            run_b = _new_run(s, ws_id)
            _store(s, workspace_id=ws_id, pipeline_run_id=run_b).write("E5", "analise", {"v": 2})
            s.commit()
            return _retention_by_run(s, ws_id), run_b

    raw = await db.connection()
    retention, run_b = await raw.run_sync(_do)
    _assert_close_to_days_from_now(retention[run_a], days=30)
    assert retention[run_b] is None, "versão corrente fica NULL permanente (fail-safe)"


@pytest.mark.asyncio
async def test_marking_is_alias_aware_across_spellings(db: AsyncSession):
    """Row legada ("E5") é superseded por write descritivo ("analyze_finances") — ADR-093."""
    ws_id, run_a = await _seed_ws_and_run(db, email="ret-alias@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            _store(s, workspace_id=ws_id, pipeline_run_id=run_a).write("E5", "analise", {"v": 1})
            s.commit()
            run_b = _new_run(s, ws_id)
            _store(s, workspace_id=ws_id, pipeline_run_id=run_b).write(
                "analyze_finances", "analise", {"v": 2}
            )
            s.commit()
            return _retention_by_run(s, ws_id), run_b

    raw = await db.connection()
    retention, run_b = await raw.run_sync(_do)
    assert retention[run_a] is not None, "grafia legada deve ser marcada pelo write descritivo"
    assert retention[run_b] is None


@pytest.mark.asyncio
async def test_same_run_overwrite_does_not_mark(db: AsyncSession):
    """UPDATE in-place (mesmo run) não é nova versão — row continua corrente/NULL."""
    ws_id, run_a = await _seed_ws_and_run(db, email="ret-upsert@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store.write("E5", "analise", {"v": 1})
            store.write("E5", "analise", {"v": 2})
            s.commit()
            rows = s.query(PipelineArtifact).filter_by(workspace_id=ws_id).all()
            return [(r.pipeline_run_id, r.retention_until) for r in rows]

    raw = await db.connection()
    rows = await raw.run_sync(_do)
    assert len(rows) == 1, "upsert no mesmo run não cria segunda versão"
    assert rows[0][1] is None


@pytest.mark.asyncio
async def test_existing_retention_is_never_extended(db: AsyncSession):
    """Terceira versão marca a segunda; o prazo da primeira não é re-estampado."""
    ws_id, run_a = await _seed_ws_and_run(db, email="ret-noextend@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            _store(s, workspace_id=ws_id, pipeline_run_id=run_a).write("E4", "despesas", {"v": 1})
            s.commit()
            run_b = _new_run(s, ws_id)
            _store(s, workspace_id=ws_id, pipeline_run_id=run_b).write("E4", "despesas", {"v": 2})
            s.commit()
            first_value = _retention_by_run(s, ws_id)[run_a]

            run_c = _new_run(s, ws_id)
            _store(s, workspace_id=ws_id, pipeline_run_id=run_c).write("E4", "despesas", {"v": 3})
            s.commit()
            after = _retention_by_run(s, ws_id)
            return first_value, after, run_b, run_c

    raw = await db.connection()
    first_value, after, run_b, run_c = await raw.run_sync(_do)
    assert after[run_a] == first_value, "prazo já atribuído nunca é estendido"
    assert after[run_b] is not None
    assert after[run_c] is None


@pytest.mark.asyncio
async def test_marking_is_scoped_by_workspace_and_key(db: AsyncSession):
    ws_a, run_a = await _seed_ws_and_run(db, email="ret-ws-a@test.com")
    ws_b, run_b = await _seed_ws_and_run(db, email="ret-ws-b@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            _store(s, workspace_id=ws_b, pipeline_run_id=run_b).write("E5", "analise", {"v": 1})
            _store(s, workspace_id=ws_a, pipeline_run_id=run_a).write("E5", "outra_key", {"v": 1})
            s.commit()
            run_a2 = _new_run(s, ws_a)
            _store(s, workspace_id=ws_a, pipeline_run_id=run_a2).write("E5", "analise", {"v": 2})
            s.commit()
            return _retention_by_run(s, ws_a), _retention_by_run(s, ws_b)

    raw = await db.connection()
    ret_a, ret_b = await raw.run_sync(_do)
    assert ret_a[run_a] is None, "artifact_key diferente não pertence ao grupo"
    assert all(v is None for v in ret_b.values()), "marking nunca cruza workspaces"
