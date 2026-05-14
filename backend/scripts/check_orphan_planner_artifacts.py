#!/usr/bin/env python3
"""Healthcheck — artifacts órfãos do parecer planejador (ADR-199 Ato 6 T-26).

Detecta `pipeline_artifacts(stage='E6-parecer', artifact_key='parecer_planejador')`
mais antigos que 1h que **não** têm `PlannerReview` correspondente — indica
falha de wire-up (`_persist_planner_review_if_applicable`) ou crash entre
stage success e materialização da projection.

Uso:

    python3 backend/scripts/check_orphan_planner_artifacts.py
    python3 backend/scripts/check_orphan_planner_artifacts.py --workspace-id <ws>
    python3 backend/scripts/check_orphan_planner_artifacts.py --fix --dry-run
    python3 backend/scripts/check_orphan_planner_artifacts.py --fix

``--fix`` cria PlannerReview retroativo a partir do ``content_json`` (last
resort, log audit). Idempotente por UNIQUE (workspace_id, pipeline_run_id).
"""

from __future__ import annotations

import argparse
import json
import logging

# Ajusta sys.path para importar backend.app quando rodado standalone.
import os as _os
import pathlib as _pl
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

_repo_root = _pl.Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
_os.environ.setdefault("MATHOMS_WORKSPACE_ROOT", str(_repo_root))

from backend.app.core.database import SyncSessionLocal  # noqa: E402
from backend.app.models.pipeline_artifact import PipelineArtifact  # noqa: E402
from backend.app.models.pipeline_run import PipelineRun  # noqa: E402
from backend.app.models.planner_review import PlannerReview  # noqa: E402

logger = logging.getLogger("mathoms.healthcheck.planner_review_orphan")
_PARECER_STAGE = "E6-parecer"
_PARECER_KEY = "parecer_planejador"
_DEFAULT_AGE_HOURS = 1


@dataclass(frozen=True)
class OrphanRow:
    artifact_id: int
    workspace_id: str
    pipeline_run_id: str
    created_at: datetime


def _find_orphans(
    db: Session,
    *,
    workspace_id: Optional[str] = None,
    age_hours: int = _DEFAULT_AGE_HOURS,
) -> list[OrphanRow]:
    """Artifacts E6-parecer sem PlannerReview correspondente e > age_hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    stmt = (
        select(
            PipelineArtifact.id,
            PipelineArtifact.workspace_id,
            PipelineArtifact.pipeline_run_id,
            PipelineArtifact.created_at,
        )
        .outerjoin(
            PlannerReview,
            PlannerReview.pipeline_artifact_id == PipelineArtifact.id,
        )
        .where(
            and_(
                PipelineArtifact.stage == _PARECER_STAGE,
                PipelineArtifact.artifact_key == _PARECER_KEY,
                PipelineArtifact.created_at < cutoff,
                PlannerReview.id.is_(None),
            )
        )
        .order_by(PipelineArtifact.created_at.asc())
    )
    if workspace_id:
        stmt = stmt.where(PipelineArtifact.workspace_id == workspace_id)
    return [
        OrphanRow(
            artifact_id=row[0],
            workspace_id=row[1],
            pipeline_run_id=row[2],
            created_at=row[3],
        )
        for row in db.execute(stmt).all()
    ]


def _find_e5_artifact_id(db: Session, *, workspace_id: str, run_id: str) -> Optional[int]:
    """Localiza ID do E5 do mesmo run — necessário pra FK ``e5_artifact_id``."""
    row = db.execute(
        select(PipelineArtifact.id).where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.pipeline_run_id == run_id,
            PipelineArtifact.stage == "E5",
            PipelineArtifact.artifact_key == "analise_financeira",
        )
    ).scalar_one_or_none()
    return row


def _retro_create_planner_review(db: Session, orphan: OrphanRow) -> Optional[str]:
    """Cria PlannerReview retroativo a partir do content_json do artifact."""
    artifact = db.get(PipelineArtifact, orphan.artifact_id)
    if artifact is None:
        return None
    e5_id = _find_e5_artifact_id(
        db, workspace_id=orphan.workspace_id, run_id=orphan.pipeline_run_id
    )
    if e5_id is None:
        logger.warning(
            "orphan_e5_missing",
            extra={"artifact_id": orphan.artifact_id, "run_id": orphan.pipeline_run_id},
        )
        return None
    meta = (
        artifact.content_json.get("metadata", {}) if isinstance(artifact.content_json, dict) else {}
    )
    review = PlannerReview(
        workspace_id=orphan.workspace_id,
        pipeline_run_id=orphan.pipeline_run_id,
        pipeline_artifact_id=orphan.artifact_id,
        e5_artifact_id=e5_id,
        status="Gerado",
        persona_hash=meta.get("persona_hash", "0" * 64),
        manifest_version=meta.get("manifest_version", "unknown"),
        schema_version=meta.get("schema_version", "unknown"),
        model_id=meta.get("model_id", "unknown"),
        tier_at_generation=meta.get("tier_at_generation", "premium"),
        items_shown_count=0,
        items_gated_count=0,
        cost_usd_cents=0,
        tokens_in=0,
        tokens_out=0,
        tool_iterations=0,
        latency_ms=0,
    )
    db.add(review)
    db.flush()
    logger.info(
        "orphan_planner_review_fixed",
        extra={
            "artifact_id": orphan.artifact_id,
            "review_id": review.id,
            "workspace_id": orphan.workspace_id,
        },
    )
    return review.id


def _report_orphans(orphans: list[OrphanRow]) -> int:
    """Log estruturado + summary. Retorna count."""
    count = len(orphans)
    if count == 0:
        logger.info("planner_review_orphan_check_clean")
        return 0
    oldest = orphans[0]
    logger.warning(
        "planner_review_orphan",
        extra={
            "count": count,
            "oldest_artifact_id": oldest.artifact_id,
            "oldest_created_at": oldest.created_at.isoformat(),
        },
    )
    return count


def _do_fix(db: Session, orphans: list[OrphanRow], *, dry_run: bool) -> int:
    """Itera órfãos, cria PlannerReview retroativo. Retorna count corrigido."""
    fixed = 0
    for o in orphans:
        if dry_run:
            logger.info(
                "orphan_would_fix",
                extra={"artifact_id": o.artifact_id, "run_id": o.pipeline_run_id},
            )
            fixed += 1
            continue
        review_id = _retro_create_planner_review(db, o)
        if review_id:
            fixed += 1
    if not dry_run:
        db.commit()
    return fixed


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry. Returns 0 = clean / 1 = orphans found / 2 = bad args."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--workspace-id", help="Filtra por workspace específico.")
    parser.add_argument(
        "--age-hours",
        type=int,
        default=_DEFAULT_AGE_HOURS,
        help=f"Idade mínima em horas (default: {_DEFAULT_AGE_HOURS}).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Cria PlannerReview retroativo (last resort).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Com --fix: simula sem persistir.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON em vez de log.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    with SyncSessionLocal() as db:
        orphans = _find_orphans(db, workspace_id=args.workspace_id, age_hours=args.age_hours)
        count = _report_orphans(orphans)
        fixed = 0
        if args.fix and orphans:
            fixed = _do_fix(db, orphans, dry_run=args.dry_run)

    if args.json:
        out = {
            "orphans_found": count,
            "fixed": fixed if args.fix else None,
            "dry_run": args.dry_run if args.fix else None,
            "rows": [
                {
                    "artifact_id": o.artifact_id,
                    "workspace_id": o.workspace_id,
                    "pipeline_run_id": o.pipeline_run_id,
                    "created_at": o.created_at.isoformat(),
                }
                for o in orphans
            ],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))

    return 1 if count > 0 and not args.fix else 0


if __name__ == "__main__":
    sys.exit(main())
