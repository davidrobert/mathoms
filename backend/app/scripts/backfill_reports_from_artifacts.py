"""Backfill: cria ``Report`` para runs ``completed`` que ficaram sem relatório.

Regressão A6c+ADR-129 (2026-04-24): com ``USE_DB_ARTIFACTS=True`` (default
desde A6c), o E5 deixou de escrever em disco e o ``_create_report_from_output``
do pipeline_task ainda buscava ``processed/E5_analysis/*-5_analysis.json``.
O resultado: pipelines marcados ``completed`` sem linha em ``reports``.

Este script encontra runs nessa situação, materializa o artefato E5 do DB
para o disco e cria a linha em ``reports`` retroativamente.

Uso::

    python -m backend.app.scripts.backfill_reports_from_artifacts --dry-run
    python -m backend.app.scripts.backfill_reports_from_artifacts --apply
    python -m backend.app.scripts.backfill_reports_from_artifacts --apply \\
        --workspace-id <uuid>
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.report import Report
from backend.app.services.storage import StorageService
from pipeline.domain.services.e5_serialization import (
    E5_ARTIFACT_FILENAME,
    E5_ARTIFACT_KEY,
    E5_OUTPUT_STAGE,
)

_BRT = ZoneInfo("America/Sao_Paulo")

_session_factory = SyncSessionLocal


def set_session_factory(factory) -> None:
    """Override do factory de sessão — usado em testes."""
    global _session_factory
    _session_factory = factory


def _runs_without_report(session: Session, workspace_id: Optional[str]) -> Iterable[PipelineRun]:
    """Runs ``completed`` cujo ``pipeline_run_id`` não aparece em ``reports``."""
    existing_run_ids = set(
        session.execute(select(Report.pipeline_run_id).where(Report.pipeline_run_id.is_not(None)))
        .scalars()
        .all()
    )
    q = select(PipelineRun).where(PipelineRun.status == PipelineRunStatus.completed)
    if workspace_id:
        q = q.where(PipelineRun.workspace_id == workspace_id)
    q = q.order_by(PipelineRun.completed_at.asc().nulls_last())
    for run in session.execute(q).scalars().all():
        if run.id in existing_run_ids:
            continue
        yield run


def _load_e5_artifact(session: Session, run: PipelineRun) -> Optional[dict]:
    row = (
        session.query(PipelineArtifact)
        .filter_by(
            workspace_id=run.workspace_id,
            pipeline_run_id=run.id,
            stage=E5_OUTPUT_STAGE,
            artifact_key=E5_ARTIFACT_KEY,
        )
        .one_or_none()
    )
    if row is None or not row.content_json:
        return None
    return row.content_json


def _materialize_to_disk(payload: dict, tenant_root: Path) -> Path:
    target_dir = tenant_root / "processed" / "E5_analysis"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / E5_ARTIFACT_FILENAME
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def _build_report(run: PipelineRun, analysis_json: Path) -> Report:
    title_ts = run.completed_at or datetime.now(_BRT)
    if title_ts.tzinfo is None:
        title_ts = title_ts.replace(tzinfo=_BRT)
    title = f"Relatório {title_ts.astimezone(_BRT).strftime('%Y-%m-%d %H:%M')}"
    return Report(
        id=str(uuid.uuid4()),
        workspace_id=run.workspace_id,
        pipeline_run_id=run.id,
        title=title,
        analysis_json_path=str(analysis_json),
        size_bytes=analysis_json.stat().st_size,
    )


def backfill(workspace_id: Optional[str], *, apply: bool, storage: StorageService) -> dict:
    summary: dict = {"runs_inspected": 0, "missing_artifact": 0, "created": 0, "errors": []}
    with _session_factory() as session:
        for run in _runs_without_report(session, workspace_id):
            summary["runs_inspected"] += 1
            payload = _load_e5_artifact(session, run)
            if payload is None:
                summary["missing_artifact"] += 1
                sys.stderr.write(
                    f"[skip] run={run.id} ws={run.workspace_id} "
                    "— sem artefato E5/analise_financeira no DB\n"
                )
                continue
            tenant_root = storage.ensure_tenant_dirs(run.workspace_id)
            try:
                analysis_json = _materialize_to_disk(payload, tenant_root)
            except OSError as exc:
                summary["errors"].append({"run_id": run.id, "error": str(exc)})
                continue
            if apply:
                session.add(_build_report(run, analysis_json))
            summary["created"] += 1
            sys.stderr.write(
                f"[{'apply' if apply else 'dry-run'}] run={run.id} "
                f"ws={run.workspace_id} → {analysis_json}\n"
            )
        if apply:
            session.commit()
    return summary


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Lista o que seria criado")
    group.add_argument("--apply", action="store_true", help="Cria os reports")
    parser.add_argument(
        "--workspace-id",
        type=str,
        default=None,
        help="Restringe a um workspace específico (UUID)",
    )
    args = parser.parse_args(argv)

    storage = StorageService()
    summary = backfill(args.workspace_id, apply=args.apply, storage=storage)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
