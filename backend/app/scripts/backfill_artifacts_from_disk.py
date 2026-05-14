"""Backfill: migra artefatos legados em ``processed/*.json`` para ``pipeline_artifacts`` (ADR-082).

Usado no cutover da Fase 4.6 para workspaces existentes que têm artefatos em
disco mas ainda não no banco. Idempotente: pular se já existe artefato para
``(workspace_id, stage, artifact_key)``.

Uso:

    python -m backend.app.scripts.backfill_artifacts_from_disk --dry-run
    python -m backend.app.scripts.backfill_artifacts_from_disk --apply
    python -m backend.app.scripts.backfill_artifacts_from_disk --apply \
        --workspace-id <uuid>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.workspace import Workspace
from pipeline.artifact_store import _STAGE_TO_DIR, _STAGE_TO_SUFFIX

# Injeção opcional para testes — default usa ``SyncSessionLocal``.
_session_factory: callable = SyncSessionLocal


def set_session_factory(factory: callable) -> None:
    """Override do factory de sessão — usado em testes para apontar para outro DB."""
    global _session_factory
    _session_factory = factory


# Stages cujos artefatos em disco são migrados. Excluímos stages que não
# produzem JSON em ``processed/``.
_MIGRATED_STAGES = [
    "E1.5c",
    "E2-extratos",
    "E2-faturas",
    "E2-llm",
    "E3",
    "E4",
    "E5",
    "E5.N",
    "E7-crossval",
]


def _iter_workspaces(workspace_id: Optional[str] = None) -> Iterable[Workspace]:
    with _session_factory() as session:
        q = select(Workspace)
        if workspace_id:
            q = q.where(Workspace.id == workspace_id)
        yield from session.execute(q).scalars().all()


def _resolve_disk_stage_path(root: Path, stage: str) -> tuple[Path, str]:
    return root / "processed" / _STAGE_TO_DIR[stage], _STAGE_TO_SUFFIX[stage]


def _get_or_create_synthetic_run(session, workspace_id: str) -> PipelineRun:
    """Usa a última run do workspace; se não houver, cria uma sintética.

    Backfill precisa de uma ``pipeline_run_id`` válida (FK). Em workspaces sem
    runs, uma run sintética marcada ``completed`` é criada como placeholder.
    """
    run = session.execute(
        select(PipelineRun)
        .where(PipelineRun.workspace_id == workspace_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if run is not None:
        return run
    run = PipelineRun(
        workspace_id=workspace_id,
        status=PipelineRunStatus.completed,
    )
    session.add(run)
    session.flush()
    return run


def _backfill_one_workspace(workspace: Workspace, *, apply: bool) -> dict:
    root = settings.STORAGE_ROOT / workspace.id
    processed = root / "processed"
    report: dict = {
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "processed_exists": processed.exists(),
        "per_stage": {},
        "migrated": 0,
        "skipped": 0,
    }
    if not processed.exists():
        return report

    with _session_factory() as session:
        run = _get_or_create_synthetic_run(session, workspace.id)
        for stage in _MIGRATED_STAGES:
            stage_dir, suffix = _resolve_disk_stage_path(root, stage)
            if not stage_dir.exists():
                continue
            found = 0
            migrated = 0
            skipped = 0
            for f in sorted(stage_dir.iterdir()):
                if not f.name.endswith(suffix):
                    continue
                key = f.name[: -len(suffix)]
                found += 1
                exists = session.execute(
                    select(PipelineArtifact)
                    .where(
                        PipelineArtifact.workspace_id == workspace.id,
                        PipelineArtifact.stage == stage,
                        PipelineArtifact.artifact_key == key,
                    )
                    .limit(1)
                ).scalar_one_or_none()
                if exists is not None:
                    skipped += 1
                    continue
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                except (OSError, json.JSONDecodeError) as e:
                    sys.stderr.write(f"[skip] {f}: {e}\n")
                    skipped += 1
                    continue
                if apply:
                    session.add(
                        PipelineArtifact(
                            workspace_id=workspace.id,
                            pipeline_run_id=run.id,
                            stage=stage,
                            artifact_key=key,
                            content_json=data,
                            byte_size=f.stat().st_size,
                        )
                    )
                migrated += 1
            report["per_stage"][stage] = {
                "found": found,
                "migrated": migrated,
                "skipped": skipped,
            }
            report["migrated"] += migrated
            report["skipped"] += skipped
        if apply:
            session.commit()
    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Lista o que seria migrado")
    group.add_argument("--apply", action="store_true", help="Aplica a migração no banco")
    parser.add_argument("--workspace-id", help="Processa apenas um workspace específico (UUID)")
    args = parser.parse_args(argv)

    any_action = False
    for ws in _iter_workspaces(args.workspace_id):
        any_action = True
        report = _backfill_one_workspace(ws, apply=args.apply)
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(
            f"[{mode}] workspace={ws.id} ({ws.name}): "
            f"migrated={report['migrated']} skipped={report['skipped']}"
        )
        for stage, s in report["per_stage"].items():
            if s["found"] > 0:
                print(
                    f"    {stage}: found={s['found']} migrated={s['migrated']} "
                    f"skipped={s['skipped']}"
                )
    if not any_action:
        print("(nenhum workspace encontrado)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
