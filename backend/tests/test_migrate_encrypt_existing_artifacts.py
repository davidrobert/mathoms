"""Tests — dev/migrate_encrypt_existing_artifacts.py (ADR-231)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.models import (
    PipelineArtifact,
    PipelineRun,
    PipelineRunStatus,
    User,
    Workspace,
)
from backend.app.services.security.crypto import is_encrypted_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

migrate_mod = importlib.import_module("dev.migrate_encrypt_existing_artifacts")


async def _seed_workspace_run(db: AsyncSession):
    user = User(email="bf@test.com", hashed_password=hash_password("p"), full_name="U")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    await db.flush()
    run = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.running)
    db.add(run)
    await db.flush()
    return ws.id, run.id


async def _seed_rows(db: AsyncSession, count: int = 5):
    ws_id, run_id = await _seed_workspace_run(db)
    for i in range(count):
        db.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage="E3",
                artifact_key=f"key_{i}",
                content_json={"plain": i},
            )
        )
    await db.flush()
    return ws_id


async def _run(db: AsyncSession, callback):
    raw = await db.connection()
    return await raw.run_sync(callback)


@pytest.mark.asyncio
async def test_count_pending_finds_plaintext_rows(db: AsyncSession):
    ws_id = await _seed_rows(db, count=3)

    def _do(sync_conn):
        with Session(sync_conn) as s:
            return migrate_mod._count_pending(s, ws_id)

    assert await _run(db, _do) == 3


@pytest.mark.asyncio
async def test_backfill_encrypts_all_and_is_idempotent(db: AsyncSession):
    ws_id = await _seed_rows(db, count=4)

    def _do(sync_conn):
        with Session(sync_conn) as s:
            before = migrate_mod._count_pending(s, ws_id)
            for row in migrate_mod._query_pending(s, ws_id, None, 10):
                row.content_json = migrate_mod.encrypt_artifact_payload(row.content_json or {})
            s.commit()
            after = migrate_mod._count_pending(s, ws_id)
            for r in s.query(PipelineArtifact).filter_by(workspace_id=ws_id).all():
                assert is_encrypted_payload(r.content_json)
            return before, after, migrate_mod._count_pending(s, ws_id)

    before, after, second = await _run(db, _do)
    assert before == 4 and after == 0 and second == 0


def test_payload_fingerprint_is_deterministic():
    assert migrate_mod._payload_fingerprint(
        {"foo": "bar", "n": 1}
    ) == migrate_mod._payload_fingerprint({"n": 1, "foo": "bar"})


def test_cursor_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(migrate_mod, "CURSOR_DIR", tmp_path)
    assert migrate_mod._read_cursor("ws-1") is None
    migrate_mod._write_cursor("ws-1", "artifact-uuid-123")
    assert migrate_mod._read_cursor("ws-1") == "artifact-uuid-123"
    migrate_mod._clear_cursor("ws-1")
    assert migrate_mod._read_cursor("ws-1") is None
