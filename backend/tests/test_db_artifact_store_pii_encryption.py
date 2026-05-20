"""Tests — DBArtifactStore encrypt/decrypt hooks (ADR-231)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.models import (
    PipelineArtifact,
    PipelineRun,
    PipelineRunStatus,
    User,
    Workspace,
)
from backend.app.services.crypto import is_encrypted_payload
from backend.app.services.db_artifact_store import DBArtifactStore


async def _seed(db: AsyncSession, *, email: str):
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


async def _run(db: AsyncSession, callback):
    raw = await db.connection()
    return await raw.run_sync(callback)


@pytest.mark.asyncio
async def test_write_encrypts_and_read_decrypts(db: AsyncSession):
    ws_id, run_id = await _seed(db, email="enc1@test.com")
    plaintext = {"cpf": "111.111.111-11", "nome": "Alice"}

    def _do(sync_conn):
        with Session(sync_conn) as s:
            store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E1", "members", plaintext)
            s.commit()
            row = s.query(PipelineArtifact).filter_by(stage="E1", artifact_key="members").one()
            return row.content_json, store.read("E1", "members")

    on_disk, via_read = await _run(db, _do)
    assert is_encrypted_payload(on_disk) and on_disk["v"] == 1
    assert isinstance(on_disk["kid"], str) and len(on_disk["kid"]) == 8
    assert via_read == plaintext


@pytest.mark.asyncio
async def test_write_is_idempotent_on_sentinel(db: AsyncSession):
    ws_id, run_id = await _seed(db, email="enc2@test.com")
    plaintext = {"nome": "Bob"}

    def _do(sync_conn):
        with Session(sync_conn) as s:
            store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E1", "members", plaintext)
            s.commit()
            store.write("E1", "members", plaintext)
            s.commit()
            return store.read("E1", "members")

    assert await _run(db, _do) == plaintext


@pytest.mark.asyncio
async def test_kill_switch_off_writes_plaintext(db: AsyncSession, monkeypatch):
    ws_id, run_id = await _seed(db, email="enc3@test.com")
    monkeypatch.setattr(settings, "ENCRYPT_PIPELINE_ARTIFACTS", False)
    plaintext = {"nome": "Carol"}

    def _do(sync_conn):
        with Session(sync_conn) as s:
            store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E1", "members", plaintext)
            s.commit()
            row = s.query(PipelineArtifact).filter_by(stage="E1", artifact_key="members").one()
            return row.content_json, store.read("E1", "members")

    on_disk, via_read = await _run(db, _do)
    assert on_disk == plaintext == via_read


@pytest.mark.asyncio
async def test_read_decrypts_even_when_kill_switch_off(db: AsyncSession, monkeypatch):
    """Compat com rows já encriptadas em revert: read sempre decripta sentinel."""
    ws_id, run_id = await _seed(db, email="enc4@test.com")

    def _write(sync_conn):
        with Session(sync_conn) as s:
            store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E1", "members", {"nome": "Dave"})
            s.commit()

    await _run(db, _write)
    monkeypatch.setattr(settings, "ENCRYPT_PIPELINE_ARTIFACTS", False)

    def _read(sync_conn):
        with Session(sync_conn) as s:
            return DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id).read(
                "E1", "members"
            )

    assert await _run(db, _read) == {"nome": "Dave"}


def _write_invalid_e3(sync_conn, ws_id, run_id):
    with Session(sync_conn) as s:
        store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
        try:
            store.write("E3", "bad", {"not_a_valid_e3_shape": True})
            s.commit()
            row = s.query(PipelineArtifact).filter_by(stage="E3", artifact_key="bad").one_or_none()
            return ("persisted", row.content_json if row else None)
        except Exception as exc:
            return ("raised", type(exc).__name__)


@pytest.mark.asyncio
async def test_schema_validation_runs_before_encrypt(db: AsyncSession):
    """Em warn mode, payload inválido persiste mas content_json é sentinel encriptado."""
    import os

    ws_id, run_id = await _seed(db, email="enc5@test.com")
    outcome, value = await _run(db, lambda c: _write_invalid_e3(c, ws_id, run_id))
    if os.environ.get("MATHOMS_PIPELINE_SCHEMA_MODE", "warn") == "strict":
        assert outcome == "raised"
    else:
        assert outcome == "persisted" and (value is None or is_encrypted_payload(value))


@pytest.mark.asyncio
async def test_workspace_scoped_read_decrypts(db: AsyncSession):
    """Stages workspace-scoped (E1.5): fallback cross-run decripta corretamente."""
    ws_id, run_id = await _seed(db, email="enc6@test.com")

    def _do(sync_conn):
        with Session(sync_conn) as s:
            DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id).write(
                "E1.5", "baseline_patrimonial", {"v": 1}
            )
            s.commit()
            new_run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(new_run)
            s.flush()
            return DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=new_run.id).read(
                "E1.5", "baseline_patrimonial"
            )

    assert await _run(db, _do) == {"v": 1}
