"""Enforcement strict + telemetria de drift no DBArtifactStore (ADR-284) — antes, ``_validate_schema`` descartava o bool de ``validate_dict`` e strict era no-op no caminho do store."""

from __future__ import annotations

import logging

import jsonschema
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
from backend.app.services.storage.db_artifact_store import DBArtifactStore
from backend.app.tasks.pipeline_task import _run_stage_with_retry

_INVALID_E3 = {"not_a_valid_e3_shape": True}


@pytest.fixture(autouse=True)
def _repo_config(monkeypatch):
    """Pinna pipeline_common no config/ real do repo — outros módulos (ex.: test_content_addressed_upload) chamam ``route_documents._init_config`` e repontam ``CONFIG_DIR`` para layout sem ``schema_validation``, o que desligaria a validação aqui."""
    from pathlib import Path

    import scripts.pipeline_common as pc

    repo_config = Path(__file__).resolve().parents[2] / "config"
    monkeypatch.setattr(pc, "CONFIG_DIR", repo_config)
    monkeypatch.setattr(pc, "_schema_registry", None)
    _patch_schema_validation(monkeypatch, {})


def _patch_schema_validation(monkeypatch, overrides: dict) -> None:
    import scripts.pipeline_common as pc

    monkeypatch.setitem(
        pc._config_cache,
        "pipeline.json",
        {"schema_validation": {"enabled": True, "mode": "warn", "mode_overrides": overrides}},
    )


def _drift_records(caplog):
    return [
        r
        for r in caplog.records
        if r.name == "mathoms.pipeline.schema_validation"
        and r.getMessage() == "schema_validation_drift"
    ]


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


def _write_invalid_e3(sync_conn, ws_id, run_id):
    with Session(sync_conn) as s:
        store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
        try:
            store.write("E3", "bad", dict(_INVALID_E3))
            s.commit()
            row = s.query(PipelineArtifact).filter_by(stage="E3", artifact_key="bad").one_or_none()
            return ("persisted", row is not None)
        except jsonschema.ValidationError:
            return ("raised", None)


@pytest.mark.asyncio
async def test_strict_env_raise_bloqueia_write(db: AsyncSession, monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    ws_id, run_id = await _seed(db, email="strict1@test.com")
    outcome, _ = await _run(db, lambda c: _write_invalid_e3(c, ws_id, run_id))
    assert outcome == "raised"


@pytest.mark.asyncio
async def test_warn_persiste_e_emite_telemetria_com_workspace(
    db: AsyncSession, monkeypatch, caplog
):
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
    caplog.set_level(logging.WARNING, logger="mathoms.pipeline.schema_validation")
    ws_id, run_id = await _seed(db, email="strict2@test.com")
    outcome, persisted = await _run(db, lambda c: _write_invalid_e3(c, ws_id, run_id))
    assert (outcome, persisted) == ("persisted", True)
    drift = _drift_records(caplog)
    assert drift, "write inválido em warn deve emitir record de drift"
    _assert_drift_context(drift[0], ws_id, run_id)


def _assert_drift_context(rec, ws_id, run_id):
    assert rec.workspace_id == str(ws_id)
    assert rec.pipeline_run_id == str(run_id)
    assert rec.stage == "E3"
    assert rec.artifact_key == "bad"
    assert rec.schema_name == "e3_reconciled.schema.json"


def _write_invalid_e5(sync_conn, ws_id, run_id):
    with Session(sync_conn) as s:
        store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
        store.write("E5", "analise_financeira", {"shape": "invalido"})
        s.commit()
        return True


@pytest.mark.asyncio
async def test_mode_override_per_schema_bloqueia_so_o_schema_alvo(db: AsyncSession, monkeypatch):
    monkeypatch.delenv("MATHOMS_PIPELINE_SCHEMA_MODE", raising=False)
    _patch_schema_validation(monkeypatch, {"e3_reconciled.schema.json": "strict"})
    ws_id, run_id = await _seed(db, email="strict3@test.com")
    outcome, _ = await _run(db, lambda c: _write_invalid_e3(c, ws_id, run_id))
    assert outcome == "raised"
    # e5_analysis não tem override → warn → write inválido prossegue.
    assert await _run(db, lambda c: _write_invalid_e5(c, ws_id, run_id)) is True


class TestValidationErrorNuncaRetenta:
    """Erro de schema é determinístico — retry queima backoff sem chance de passar."""

    def test_validation_error_nao_retenta_mesmo_com_texto_retryable(self, monkeypatch):
        import backend.app.tasks.pipeline_task as pt

        monkeypatch.setattr(
            pt.time, "sleep", lambda *_: pytest.fail("retry de ValidationError dormiu backoff")
        )
        calls = []

        def _stage(ctx, stage_name):
            calls.append(stage_name)
            raise jsonschema.ValidationError("connection timeout 503 rate_limit")

        result, attempts, error_msg, tb = _run_stage_with_retry(None, "E2-llm", _stage)
        assert result is None
        assert attempts == 1
        assert len(calls) == 1
        assert "rate_limit" in error_msg

    def test_erro_transiente_continua_retentavel(self, monkeypatch):
        import backend.app.tasks.pipeline_task as pt

        sleeps = []
        monkeypatch.setattr(pt.time, "sleep", sleeps.append)
        calls = []

        def _stage(ctx, stage_name):
            calls.append(stage_name)
            raise RuntimeError("connection timeout")

        result, attempts, _, _ = _run_stage_with_retry(None, "E2-llm", _stage)
        assert result is None
        assert attempts == 3  # 1 tentativa + 2 retries (STAGE_RETRY_CONFIGS["E2-llm"])
        assert len(sleeps) == 2
