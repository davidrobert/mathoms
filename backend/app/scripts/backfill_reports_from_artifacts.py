"""Backfill: cria ``Report`` para runs ``completed`` que ficaram sem relatório.

Regressão A6c+ADR-129 (2026-04-24): com ``USE_DB_ARTIFACTS=True`` (default
desde A6c), o E5 deixou de escrever em disco e o ``_create_report_from_output``
do pipeline_task ainda buscava ``processed/E5_analysis/*-5_analysis.json``.
O resultado: pipelines marcados ``completed`` sem linha em ``reports``.

ADR-131 (2026-04-25): o relatório passou a referenciar o artefato E5 por
FK (``analysis_artifact_id``); este backfill agora cria a linha
``reports`` apontando direto para a row em ``pipeline_artifacts`` — sem
materializar nada em disco.

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
from decimal import Decimal
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.report import Report
from pipeline.artifact_store import stage_aliases
from pipeline.domain.services.e5_serialization import E5_ARTIFACT_KEY, E5_OUTPUT_STAGE

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


def _find_e5_artifact(session: Session, run: PipelineRun) -> Optional[PipelineArtifact]:
    return (
        session.query(PipelineArtifact)
        .filter(
            PipelineArtifact.workspace_id == run.workspace_id,
            PipelineArtifact.pipeline_run_id == run.id,
            PipelineArtifact.stage.in_(stage_aliases(E5_OUTPUT_STAGE)),
            PipelineArtifact.artifact_key == E5_ARTIFACT_KEY,
        )
        .one_or_none()
    )


def _build_report(run: PipelineRun, artifact: PipelineArtifact) -> Report:
    from backend.app.services.security.crypto import read_artifact_content

    title_ts = run.completed_at or datetime.now(_BRT)
    if title_ts.tzinfo is None:
        title_ts = title_ts.replace(tzinfo=_BRT)
    title = f"Relatório {title_ts.astimezone(_BRT).strftime('%Y-%m-%d %H:%M')}"
    score, patrimonio_liquido = Report.denorm_from_analysis(
        read_artifact_content(artifact.content_json)
    )
    return Report(
        id=str(uuid.uuid4()),
        workspace_id=run.workspace_id,
        pipeline_run_id=run.id,
        title=title,
        analysis_artifact_id=artifact.id,
        score=score,
        patrimonio_liquido=patrimonio_liquido,
    )


def _reports_missing_columns(session: Session, workspace_id: Optional[str] = None) -> list[Report]:
    """Reports com artefato E5 mas ``score``/``patrimonio_liquido`` NULL (ADR-326)."""
    q = select(Report).where(
        Report.analysis_artifact_id.is_not(None),
        or_(Report.score.is_(None), Report.patrimonio_liquido.is_(None)),
    )
    if workspace_id:
        q = q.where(Report.workspace_id == workspace_id)
    return list(session.execute(q).scalars().all())


def _report_column_values(
    session: Session, report: Report
) -> tuple[str, float | None, Decimal | None]:
    """Resolve (status, score, patrimonio_liquido) de um report; status: no_artifact|noop|ok. Sem mutação."""
    from backend.app.services.security.crypto import read_artifact_content

    artifact = session.get(PipelineArtifact, report.analysis_artifact_id)
    if artifact is None or not artifact.content_json:
        return "no_artifact", None, None
    score, pl = Report.denorm_from_analysis(read_artifact_content(artifact.content_json))
    if score is None and pl is None:
        return "noop", None, None
    return "ok", score, pl


def backfill_columns(workspace_id: Optional[str] = None, *, apply: bool) -> dict:
    """ADR-326: popula ``score``/``patrimonio_liquido`` em Reports legados (colunas NULL)."""
    summary: dict = {"reports_inspected": 0, "updated": 0, "no_artifact": 0}
    with _session_factory() as session:
        for report in _reports_missing_columns(session, workspace_id):
            summary["reports_inspected"] += 1
            status, score, pl = _report_column_values(session, report)
            if status != "ok":
                if status == "no_artifact":
                    summary["no_artifact"] += 1
                continue
            if apply:
                report.score, report.patrimonio_liquido = score, pl
            summary["updated"] += 1
            sys.stderr.write(
                f"[{'apply' if apply else 'dry-run'}] report={report.id} score={score} pl={pl}\n"
            )
        if apply:
            session.commit()
    return summary


def backfill(workspace_id: Optional[str], *, apply: bool) -> dict:
    summary: dict = {"runs_inspected": 0, "missing_artifact": 0, "created": 0}
    with _session_factory() as session:
        for run in _runs_without_report(session, workspace_id):
            summary["runs_inspected"] += 1
            artifact = _find_e5_artifact(session, run)
            if artifact is None or not artifact.content_json:
                summary["missing_artifact"] += 1
                sys.stderr.write(
                    f"[skip] run={run.id} ws={run.workspace_id} "
                    "— sem artefato E5/analise_financeira no DB\n"
                )
                continue
            if apply:
                session.add(_build_report(run, artifact))
            summary["created"] += 1
            sys.stderr.write(
                f"[{'apply' if apply else 'dry-run'}] run={run.id} "
                f"ws={run.workspace_id} → artifact_id={artifact.id}\n"
            )
        if apply:
            session.commit()
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Lista o que seria criado")
    group.add_argument("--apply", action="store_true", help="Cria os reports")
    parser.add_argument(
        "--workspace-id", type=str, default=None, help="Restringe a um workspace específico (UUID)"
    )
    parser.add_argument(
        "--backfill-columns",
        action="store_true",
        help="Popula score/patrimonio_liquido em Reports existentes com coluna NULL (ADR-326)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    runner = backfill_columns if args.backfill_columns else backfill
    summary = runner(args.workspace_id, apply=args.apply)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
