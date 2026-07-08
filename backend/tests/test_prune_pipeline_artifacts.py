"""Prune de ``pipeline_artifacts`` (A33.l6 · W6-T05): predicado de 1 ramo
(corrente nunca prunada, NULL nunca prunado), backfill idempotente com relógio
do sucessor, exclusão de rows referenciadas por FK (reports/publicações/
pareceres), gate que bloqueia delete, dry-run que nunca deleta, task beat
fim-a-fim e cascade DB-level pré-existente sob a coluna nova."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import PipelineArtifact, PipelineRun, PipelineRunStatus, User, Workspace
from backend.app.services.storage.artifact_prune import (
    build_prune_report,
    delete_expired_rows,
    mark_superseded_rows,
    run_artifact_prune,
)
from backend.app.services.storage.artifact_retention import ArtifactRetentionPolicy

_DRY_RUN = ArtifactRetentionPolicy(superseded_days=30, prune_mode="dry_run")
_DELETE = ArtifactRetentionPolicy(superseded_days=30, prune_mode="delete")

_PAST = datetime.now(timezone.utc) - timedelta(days=1)
_FUTURE = datetime.now(timezone.utc) + timedelta(days=30)


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


def _artifact(
    s,
    *,
    ws_id: str,
    run_id: str,
    stage: str = "E5",
    key: str = "analise",
    created_at: datetime | None = None,
    retention_until: datetime | None = None,
    document_id: str | None = None,
) -> int:
    row = PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage=stage,
        artifact_key=key,
        content_json={"payload": "x" * 32},
        created_at=created_at or datetime.now(timezone.utc),
        retention_until=retention_until,
        document_id=document_id,
    )
    s.add(row)
    s.flush()
    return row.id


def _new_run(s, ws_id: str) -> str:
    run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
    s.add(run)
    s.flush()
    return run.id


def _surviving_ids(s, ws_id: str) -> set[int]:
    rows = s.query(PipelineArtifact.id).filter(PipelineArtifact.workspace_id == ws_id).all()
    return {r[0] for r in rows}


# =============================================================================
# Predicado de 1 ramo
# =============================================================================


@pytest.mark.asyncio
async def test_delete_mode_prunes_only_expired_superseded(db: AsyncSession):
    """v1/v2 expiradas caem; corrente (NULL) e superseded futura sobrevivem."""
    ws_id, run_a = await _seed_ws_and_run(db, email="prune-basic@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            base = datetime.now(timezone.utc) - timedelta(days=300)
            v1 = _artifact(s, ws_id=ws_id, run_id=run_a, created_at=base, retention_until=_PAST)
            run_b = _new_run(s, ws_id)
            v2 = _artifact(
                s,
                ws_id=ws_id,
                run_id=run_b,
                created_at=base + timedelta(days=1),
                retention_until=_FUTURE,
            )
            run_c = _new_run(s, ws_id)
            v3 = _artifact(s, ws_id=ws_id, run_id=run_c, created_at=base + timedelta(days=2))
            s.commit()

            outcome = run_artifact_prune(s, policy=_DELETE, now=datetime.now(timezone.utc))
            s.commit()
            return outcome, _surviving_ids(s, ws_id), (v1, v2, v3)

    raw = await db.connection()
    outcome, surviving, (v1, v2, v3) = await raw.run_sync(_do)
    assert outcome.deleted == 1
    assert v1 not in surviving, "superseded expirada deve ser prunada"
    assert v2 in surviving, "superseded com prazo futuro sobrevive"
    assert v3 in surviving, "versão corrente sobrevive"
    assert outcome.report.gate_current_with_retention == 0


@pytest.mark.asyncio
async def test_null_retention_never_pruned(db: AsyncSession):
    """NULL ≡ fail-safe permanente — nunca entra no conjunto prunável."""
    ws_id, run_a = await _seed_ws_and_run(db, email="prune-null@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            old = datetime.now(timezone.utc) - timedelta(days=999)
            _artifact(s, ws_id=ws_id, run_id=run_a, created_at=old, key="unica_versao")
            s.commit()
            report = build_prune_report(s, now=datetime.now(timezone.utc))
            deleted = delete_expired_rows(
                s, report.expired_prunable_ids, now=datetime.now(timezone.utc)
            )
            s.commit()
            return report, deleted, len(_surviving_ids(s, ws_id))

    raw = await db.connection()
    report, deleted, remaining = await raw.run_sync(_do)
    assert report.expired_total == 0
    assert deleted == 0
    assert remaining == 1


@pytest.mark.asyncio
async def test_current_version_never_pruned_and_gate_blocks_delete(db: AsyncSession):
    """Corrente com retention expirada (invariante violada) → gate > 0 bloqueia
    o delete inteiro, mesmo em prune_mode=delete; nenhuma row cai."""
    ws_id, run_a = await _seed_ws_and_run(db, email="prune-gate@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            base = datetime.now(timezone.utc) - timedelta(days=300)
            _artifact(s, ws_id=ws_id, run_id=run_a, created_at=base, retention_until=_PAST)
            run_b = _new_run(s, ws_id)
            _artifact(
                s,
                ws_id=ws_id,
                run_id=run_b,
                created_at=base + timedelta(days=1),
                retention_until=_PAST,  # corrente com retention ≠ NULL — violação
            )
            s.commit()
            outcome = run_artifact_prune(s, policy=_DELETE, now=datetime.now(timezone.utc))
            s.commit()
            return outcome, len(_surviving_ids(s, ws_id))

    raw = await db.connection()
    outcome, remaining = await raw.run_sync(_do)
    assert outcome.report.gate_current_with_retention == 1
    assert outcome.delete_blocked_by_gate is True
    assert outcome.deleted == 0
    assert remaining == 2, "gate violado → nada é deletado (fail-safe)"


@pytest.mark.asyncio
async def test_dry_run_reports_but_never_deletes(db: AsyncSession):
    ws_id, run_a = await _seed_ws_and_run(db, email="prune-dry@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            base = datetime.now(timezone.utc) - timedelta(days=300)
            _artifact(s, ws_id=ws_id, run_id=run_a, created_at=base, retention_until=_PAST)
            run_b = _new_run(s, ws_id)
            _artifact(s, ws_id=ws_id, run_id=run_b, created_at=base + timedelta(days=1))
            s.commit()
            outcome = run_artifact_prune(s, policy=_DRY_RUN, now=datetime.now(timezone.utc))
            s.commit()
            return outcome, len(_surviving_ids(s, ws_id))

    raw = await db.connection()
    outcome, remaining = await raw.run_sync(_do)
    assert outcome.deleted == 0
    assert outcome.report.expired_total == 1
    assert len(outcome.report.expired_prunable_ids) == 1
    assert remaining == 2


# =============================================================================
# Rows referenciadas por FK nunca são prunadas
# =============================================================================


def _seed_expired_superseded_pair(s, ws_id: str, run_a: str, *, key: str) -> int:
    """Grupo com superseded expirada + corrente; retorna id da expirada."""
    base = datetime.now(timezone.utc) - timedelta(days=300)
    expired_id = _artifact(
        s, ws_id=ws_id, run_id=run_a, key=key, created_at=base, retention_until=_PAST
    )
    run_b = _new_run(s, ws_id)
    _artifact(s, ws_id=ws_id, run_id=run_b, key=key, created_at=base + timedelta(days=1))
    return expired_id


@pytest.mark.asyncio
async def test_rows_referenced_by_report_publication_and_review_survive(db: AsyncSession):
    from backend.app.models.planner_review import PlannerReview
    from backend.app.models.report import Report
    from backend.app.models.report_publication import ReportPublication

    ws_id, run_a = await _seed_ws_and_run(db, email="prune-fk@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            ref_report = _seed_expired_superseded_pair(s, ws_id, run_a, key="por_report")
            ref_publication = _seed_expired_superseded_pair(s, ws_id, run_a, key="por_pub")
            ref_review = _seed_expired_superseded_pair(s, ws_id, run_a, key="por_parecer")
            ref_review_e5 = _seed_expired_superseded_pair(s, ws_id, run_a, key="por_parecer_e5")
            unreferenced = _seed_expired_superseded_pair(s, ws_id, run_a, key="sem_ref")

            s.add(
                Report(
                    workspace_id=ws_id,
                    pipeline_run_id=run_a,
                    title="R",
                    analysis_artifact_id=ref_report,
                )
            )
            s.add(
                ReportPublication(
                    workspace_id=ws_id,
                    period_yyyymm="202606",
                    artifact_id=ref_publication,
                    published_at=datetime.now(timezone.utc),
                    published_by="ops",
                    immutable_hash="h" * 64,
                )
            )
            s.add(
                PlannerReview(
                    workspace_id=ws_id,
                    pipeline_run_id=run_a,
                    pipeline_artifact_id=ref_review,
                    e5_artifact_id=ref_review_e5,
                    persona_hash="p" * 64,
                    manifest_version="1.0",
                    schema_version="1.0",
                    model_id="claude-sonnet-4-6",
                    tier_at_generation="free",
                )
            )
            s.commit()

            outcome = run_artifact_prune(s, policy=_DELETE, now=datetime.now(timezone.utc))
            s.commit()
            survivors = _surviving_ids(s, ws_id)
            return (
                outcome,
                survivors,
                (
                    ref_report,
                    ref_publication,
                    ref_review,
                    ref_review_e5,
                    unreferenced,
                ),
            )

    raw = await db.connection()
    outcome, survivors, ids = await raw.run_sync(_do)
    ref_report, ref_publication, ref_review, ref_review_e5, unreferenced = ids
    assert outcome.report.referenced_excluded == 4
    assert outcome.deleted == 1
    for rid, label in [
        (ref_report, "reports SET NULL"),
        (ref_publication, "report_publications RESTRICT"),
        (ref_review, "planner_review CASCADE"),
        (ref_review_e5, "planner_review e5 RESTRICT"),
    ]:
        assert rid in survivors, f"row referenciada ({label}) nunca pode ser prunada"
    assert unreferenced not in survivors


# =============================================================================
# Backfill contínuo idempotente
# =============================================================================


@pytest.mark.asyncio
async def test_backfill_marks_with_successor_clock_and_is_idempotent(db: AsyncSession):
    """retention = created_at do sucessor + dias (relógio da supersessão real);
    segunda passada marca 0 e não re-estampa valores."""
    ws_id, run_a = await _seed_ws_and_run(db, email="backfill@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            base = datetime.now(timezone.utc) - timedelta(days=100)
            v1 = _artifact(s, ws_id=ws_id, run_id=run_a, stage="E5", created_at=base)
            run_b = _new_run(s, ws_id)
            v2_created = base + timedelta(days=10)
            v2 = _artifact(
                s,
                ws_id=ws_id,
                run_id=run_b,
                stage="analyze_finances",  # grafia descritiva — grupo alias-aware
                created_at=v2_created,
            )
            run_c = _new_run(s, ws_id)
            v3 = _artifact(
                s, ws_id=ws_id, run_id=run_c, stage="E5", created_at=base + timedelta(days=20)
            )
            s.commit()

            first_marked = mark_superseded_rows(s, policy=_DRY_RUN)
            s.commit()
            second_marked = mark_superseded_rows(s, policy=_DRY_RUN)
            s.commit()
            rows = {
                r.id: r.retention_until
                for r in s.query(PipelineArtifact).filter_by(workspace_id=ws_id)
            }
            return first_marked, second_marked, rows, (v1, v2, v3), v2_created

    raw = await db.connection()
    first_marked, second_marked, rows, (v1, v2, v3), v2_created = await raw.run_sync(_do)
    assert first_marked == 2
    assert second_marked == 0, "backfill é idempotente (WHERE retention_until IS NULL)"
    v1_until = rows[v1].replace(tzinfo=timezone.utc) if rows[v1].tzinfo is None else rows[v1]
    assert v1_until == v2_created + timedelta(days=30), "relógio conta do sucessor"
    assert rows[v2] is not None
    assert rows[v3] is None, "corrente nunca é marcada pelo backfill"


# =============================================================================
# Relatório do dry-run (aceite #2 + decisão #4)
# =============================================================================


@pytest.mark.asyncio
async def test_report_aggregates_workspace_stage_orphans_and_top_groups(db: AsyncSession):
    ws_id, run_a = await _seed_ws_and_run(db, email="report@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            base = datetime.now(timezone.utc) - timedelta(days=300)
            # Grupo E2 com 2 superseded (ambas órfãs de documento) + corrente.
            # Unique (run, stage, key) → cada versão vive num run próprio.
            for i, ret in enumerate([_PAST, _FUTURE]):
                _artifact(
                    s,
                    ws_id=ws_id,
                    run_id=run_a if i == 0 else _new_run(s, ws_id),
                    stage="E2-extratos",
                    key="itau_202601",
                    created_at=base + timedelta(days=i),
                    retention_until=ret,
                )
            run_b = _new_run(s, ws_id)
            _artifact(
                s,
                ws_id=ws_id,
                run_id=run_b,
                stage="extract_statements",
                key="itau_202601",
                created_at=base + timedelta(days=5),
            )
            s.commit()
            return build_prune_report(s, now=datetime.now(timezone.utc))

    raw = await db.connection()
    report = await raw.run_sync(_do)
    assert report.scanned_rows == 3
    assert report.candidates_total == 2
    assert report.candidates_bytes > 0
    assert report.expired_total == 1
    assert report.orphan_document_candidates == 2, "E2 superseded sem document_id conta como órfã"
    assert report.gate_current_with_retention == 0

    [ws_stage] = report.by_workspace_stage
    assert ws_stage["workspace_id"] == ws_id
    assert ws_stage["stage"] == "extract_statements", "agregação usa nome descritivo canônico"
    assert ws_stage["count"] == 2
    assert ws_stage["expired"] == 1

    [created_stats] = report.created_at_by_stage
    assert created_stats["stage"] == "extract_statements"
    assert created_stats["count"] == 2
    assert (
        created_stats["created_min"]
        <= created_stats["created_p50"]
        <= (created_stats["created_max"])
    )

    [top] = report.top_superseded_groups
    assert top["artifact_key"] == "itau_202601"
    assert top["superseded"] == 2

    extra = report.to_log_extra()
    assert "expired_prunable_ids" not in extra, "ids não vazam para o log estruturado"


# =============================================================================
# Task Celery beat fim-a-fim (padrão test_purge_audit_logs)
# =============================================================================


def _orm_artifact(ws_id: str, run_id: str, **kw) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E5",
        artifact_key="analise",
        content_json={"v": 1},
        **kw,
    )


async def _seed_expired_and_current_via_orm(db: AsyncSession, ws_id: str, run_a: str) -> None:
    base = datetime.now(timezone.utc) - timedelta(days=300)
    db.add(_orm_artifact(ws_id, run_a, created_at=base, retention_until=_PAST))
    run_b = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
    db.add(run_b)
    await db.flush()
    db.add(_orm_artifact(ws_id, run_b.id, created_at=base + timedelta(days=1)))
    await db.commit()


async def _remaining_artifacts(db: AsyncSession, ws_id: str) -> list[PipelineArtifact]:
    await db.rollback()
    result = await db.execute(
        sa.select(PipelineArtifact).where(PipelineArtifact.workspace_id == ws_id)
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_prune_task_dry_run_default_reports_without_deleting(
    db: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setenv("MATHOMS_ARTIFACT_PRUNE_MODE", "dry_run")
    ws_id, run_a = await _seed_ws_and_run(db, email="task-dry@test.com")
    await _seed_expired_and_current_via_orm(db, ws_id, run_a)

    from backend.app.tasks.prune_artifacts import prune_pipeline_artifacts

    result = prune_pipeline_artifacts.run()
    assert result["prune_mode"] == "dry_run"
    assert result["expired_total"] == 1
    assert result["deleted"] == 0

    remaining = await _remaining_artifacts(db, ws_id)
    assert len(remaining) == 2, "dry_run nunca deleta"


@pytest.mark.asyncio
async def test_prune_task_delete_mode_prunes_expired(db: AsyncSession, monkeypatch) -> None:
    monkeypatch.setenv("MATHOMS_ARTIFACT_PRUNE_MODE", "delete")
    ws_id, run_a = await _seed_ws_and_run(db, email="task-del@test.com")
    await _seed_expired_and_current_via_orm(db, ws_id, run_a)

    from backend.app.tasks.prune_artifacts import prune_pipeline_artifacts

    result = prune_pipeline_artifacts.run()
    assert result["prune_mode"] == "delete"
    assert result["deleted"] == 1
    assert result["delete_blocked_by_gate"] is False

    remaining = await _remaining_artifacts(db, ws_id)
    assert len(remaining) == 1
    assert remaining[0].retention_until is None, "sobrevivente é a corrente (NULL)"
