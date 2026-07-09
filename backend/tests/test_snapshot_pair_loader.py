"""Integration tests — ``snapshot_pair_loader``: 2 reports / compat ADR-093 / hash on-read (v2.D.1 · ADR-148)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

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
from backend.app.services.snapshot_pair_loader import (
    _canonical_json,
    _compute_analysis_hash,
    _extract_period_yyyymm,
    load_snapshot_pair,
)

_NOW = datetime(2026, 4, 15, tzinfo=timezone.utc)


async def _seed_user_workspace(db: AsyncSession, name: str) -> str:
    """Cria user + workspace; devolve `workspace_id`."""
    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"snap-{suffix}@test.com",
        hashed_password=hash_password("p"),
        full_name=name,
    )
    db.add(user)
    await db.flush()
    ws = Workspace(name=f"{name}-{suffix}", owner_id=user.id)
    db.add(ws)
    await db.flush()
    await db.commit()
    return ws.id


def _new_run(session: Session, workspace_id: str) -> str:
    """Cria PipelineRun (UQ `(run, stage, key)` exige runs distintas por artefato)."""
    run = PipelineRun(workspace_id=workspace_id, status=PipelineRunStatus.completed)
    session.add(run)
    session.flush()
    return run.id


def _add_artifact(session: Session, **kw) -> int:
    """Insere PipelineArtifact (run novo internamente); retorna `id`."""
    artifact = PipelineArtifact(
        workspace_id=kw["workspace_id"],
        pipeline_run_id=_new_run(session, kw["workspace_id"]),
        stage=kw["stage"],
        artifact_key="analise_financeira",
        content_json=kw["content"],
        created_at=kw["created_at"],
    )
    session.add(artifact)
    session.flush()
    session.commit()
    return artifact.id


_OLD_CONTENT = {
    "periodo_dados": "2026-01-01 a 2026-03-31",
    "patrimonio": {"liquido": 1000.0, "bruto": 1500.0},
}
_NEW_CONTENT = {
    "periodo_dados": "2026-01-01 a 2026-04-30",
    "patrimonio": {"liquido": 1100.0, "bruto": 1600.0},
}


def _seed_two_reports(session: Session, ws_id: str) -> int:
    """Seed 2 snapshots `analyze_finances` (t-1 + atual); retorna id do atual."""
    _add_artifact(
        session,
        workspace_id=ws_id,
        stage="analyze_finances",
        created_at=_NOW - timedelta(days=30),
        content=_OLD_CONTENT,
    )
    return _add_artifact(
        session,
        workspace_id=ws_id,
        stage="analyze_finances",
        created_at=_NOW,
        content=_NEW_CONTENT,
    )


def _seed_legacy_then_descritivo(session: Session, ws_id: str) -> int:
    """Seed 1 snapshot stage='E5' (legado) + 1 stage='analyze_finances'; retorna id do atual."""
    _add_artifact(
        session,
        workspace_id=ws_id,
        stage="E5",
        created_at=_NOW - timedelta(days=60),
        content={"periodo_dados": "2026-02", "patrimonio": {"liquido": 500.0}},
    )
    return _add_artifact(
        session,
        workspace_id=ws_id,
        stage="analyze_finances",
        created_at=_NOW,
        content={"periodo_dados": "2026-04", "patrimonio": {"liquido": 700.0}},
    )


def _seed_single_report(session: Session, ws_id: str) -> int:
    """Seed 1 snapshot único; retorna id."""
    return _add_artifact(
        session,
        workspace_id=ws_id,
        stage="analyze_finances",
        created_at=_NOW,
        content={"periodo_dados": "2026-04", "patrimonio": {"liquido": 1000.0}},
    )


@pytest.mark.asyncio
async def test_load_snapshot_pair_two_reports(db: AsyncSession):
    """2 reports → atual + anterior carregados; mais recente vence em `prev`."""
    ws_id = await _seed_user_workspace(db, "two-reports")

    def _run(s: Session) -> tuple:
        new_id = _seed_two_reports(s, ws_id)
        return load_snapshot_pair(s, workspace_id=ws_id, current_artifact_id=new_id)

    prev, curr = await db.run_sync(_run)
    assert prev is not None
    assert curr.workspace_id == ws_id
    assert curr.period_yyyymm == "202604"
    assert prev.period_yyyymm == "202603"
    assert curr.content_json["patrimonio"]["liquido"] == 1100.0
    assert prev.content_json["patrimonio"]["liquido"] == 1000.0


@pytest.mark.asyncio
async def test_load_snapshot_pair_legacy_stage_compat(db: AsyncSession):
    """ADR-093: `stage='E5'` (legado) + `stage='analyze_finances'` ambos elegíveis."""
    ws_id = await _seed_user_workspace(db, "legacy-stage")

    def _run(s: Session) -> tuple:
        new_id = _seed_legacy_then_descritivo(s, ws_id)
        return load_snapshot_pair(s, workspace_id=ws_id, current_artifact_id=new_id)

    prev, curr = await db.run_sync(_run)
    assert prev is not None
    assert prev.period_yyyymm == "202602"
    assert curr.period_yyyymm == "202604"


@pytest.mark.asyncio
async def test_load_snapshot_pair_first_report(db: AsyncSession):
    """Único report do workspace → `prev=None`."""
    ws_id = await _seed_user_workspace(db, "first-report")

    def _run(s: Session) -> tuple:
        new_id = _seed_single_report(s, ws_id)
        return load_snapshot_pair(s, workspace_id=ws_id, current_artifact_id=new_id)

    prev, curr = await db.run_sync(_run)
    assert prev is None
    assert curr.workspace_id == ws_id


@pytest.mark.asyncio
async def test_load_snapshot_pair_unknown_id_raises(db: AsyncSession):
    """`current_artifact_id` inexistente → ValueError."""
    ws_id = await _seed_user_workspace(db, "unknown-id")

    def _run(s: Session) -> None:
        with pytest.raises(ValueError, match="não encontrado"):
            load_snapshot_pair(s, workspace_id=ws_id, current_artifact_id=99999)

    await db.run_sync(_run)


# ---------- Helpers puros (não exigem DB) ----------


def test_canonical_json_estavel_independente_da_ordem():
    """Mesmo dict em ordem de chaves diferente → mesmo `analysis_hash`."""
    a = {"b": 2, "a": {"y": 1, "x": 2}, "c": [1, 2, 3]}
    b = {"a": {"x": 2, "y": 1}, "c": [1, 2, 3], "b": 2}
    assert _canonical_json(a) == _canonical_json(b)
    assert _compute_analysis_hash(a) == _compute_analysis_hash(b)


def test_canonical_json_decimal_via_str():
    """`Decimal` serializa via str (ADR-090) — wire estável independente de fonte."""
    from decimal import Decimal

    payload = {"x": Decimal("1.23")}
    canonical = _canonical_json(payload)
    assert "1.23" in canonical
    assert _compute_analysis_hash(payload) == _compute_analysis_hash({"x": Decimal("1.23")})


def test_extract_period_yyyymm_formatos_diversos():
    """Cobre os formatos comuns do `periodo_dados` (E5)."""
    assert _extract_period_yyyymm({"periodo_dados": "2026-01-01 a 2026-04-30"}) == "202604"
    assert _extract_period_yyyymm({"periodo_dados": "2025-12 a 2026-04"}) == "202604"
    assert _extract_period_yyyymm({"periodo_dados": "202601 a 202604"}) == "202604"
    assert _extract_period_yyyymm({"periodo": "2026-04"}) == "202604"
    assert _extract_period_yyyymm({}) == ""


_RERUN_CONTENT = {**_NEW_CONTENT, "patrimonio": {"liquido": 1050.0, "bruto": 1550.0}}


def _seed_series(session: Session, ws_id: str, specs: list[tuple[dict, datetime]]) -> int:
    """Insere N artifacts `analyze_finances`; retorna o id do último (atual)."""
    last_id = 0
    for content, created_at in specs:
        last_id = _add_artifact(
            session,
            workspace_id=ws_id,
            stage="analyze_finances",
            content=content,
            created_at=created_at,
        )
    return last_id


def _pair_for_series(session: Session, ws_id: str, specs: list[tuple[dict, datetime]]) -> tuple:
    curr_id = _seed_series(session, ws_id, specs)
    return load_snapshot_pair(session, workspace_id=ws_id, current_artifact_id=curr_id)


@pytest.mark.asyncio
async def test_rerun_do_mesmo_periodo_nao_vira_prev(db: AsyncSession):
    """ADR-190 §Emenda: prev por PERÍODO — re-run do mesmo mês é pulado."""
    ws_id = await _seed_user_workspace(db, "Rerun")
    specs = [
        (_OLD_CONTENT, datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)),
        (_RERUN_CONTENT, datetime(2026, 4, 30, 11, 0, tzinfo=timezone.utc)),
        (_NEW_CONTENT, datetime(2026, 4, 30, 11, 30, tzinfo=timezone.utc)),
    ]
    prev, curr = await db.run_sync(lambda s: _pair_for_series(s, ws_id, specs))
    assert curr.period_yyyymm == "202604"
    assert prev is not None
    assert prev.period_yyyymm == "202603"
    assert prev.content_json["patrimonio"]["liquido"] == 1000.0


@pytest.mark.asyncio
async def test_apenas_reruns_do_mesmo_periodo_sem_prev(db: AsyncSession):
    """Só re-runs do mesmo período ⇒ prev=None — nunca run-vs-rerun."""
    ws_id = await _seed_user_workspace(db, "SoRerun")
    specs = [
        (_RERUN_CONTENT, datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc)),
        (_NEW_CONTENT, datetime(2026, 4, 30, 11, 0, tzinfo=timezone.utc)),
    ]
    prev, curr = await db.run_sync(lambda s: _pair_for_series(s, ws_id, specs))
    assert prev is None
