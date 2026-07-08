"""Task Celery beat — prune diário de ``pipeline_artifacts`` (A33.l6 · W6-T05 · ADR-212).

Default ``prune_mode=dry_run``: backfill contínuo + relatório estruturado,
zero deletes. Flip para ``delete`` é PR separado, condicionado ao dry-run
registrado com ``gate_current_with_retention == 0`` (aceite da lane).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.app.core.database import SyncSessionLocal
from backend.app.services.storage.artifact_prune import ArtifactPruneOutcome, run_artifact_prune
from backend.app.services.storage.artifact_retention import (
    ArtifactRetentionPolicy,
    load_artifact_retention_policy,
)
from backend.app.worker import celery_app

logger = logging.getLogger("mathoms.pipeline.artifact")


def _log_outcome(outcome: ArtifactPruneOutcome, policy: ArtifactRetentionPolicy) -> None:
    extra = {
        "prune_mode": policy.prune_mode,
        "superseded_days": policy.superseded_days,
        "marked": outcome.marked,
        "deleted": outcome.deleted,
        **outcome.report.to_log_extra(),
    }
    if outcome.delete_blocked_by_gate:
        logger.error("mathoms.pipeline.artifact.prune_gate_blocked", extra=extra)
        return
    logger.info("mathoms.pipeline.artifact.prune_report", extra=extra)


def _summary(outcome: ArtifactPruneOutcome, policy: ArtifactRetentionPolicy) -> dict:
    report = outcome.report
    return {
        "prune_mode": policy.prune_mode,
        "marked": outcome.marked,
        "deleted": outcome.deleted,
        "delete_blocked_by_gate": outcome.delete_blocked_by_gate,
        "scanned_rows": report.scanned_rows,
        "candidates_total": report.candidates_total,
        "candidates_bytes": report.candidates_bytes,
        "expired_total": report.expired_total,
        "expired_bytes": report.expired_bytes,
        "referenced_excluded": report.referenced_excluded,
        "gate_current_with_retention": report.gate_current_with_retention,
    }


@celery_app.task(name="fin.prune_pipeline_artifacts", bind=True, max_retries=1)
def prune_pipeline_artifacts(self) -> dict:
    """Backfill superseded + relatório dry-run + (gate zerado e ``delete``) prune."""
    policy = load_artifact_retention_policy()
    now = datetime.now(timezone.utc)
    with SyncSessionLocal() as db:
        outcome = run_artifact_prune(db, policy=policy, now=now)
        db.commit()
    _log_outcome(outcome, policy)
    result = _summary(outcome, policy)
    logger.info("prune_pipeline_artifacts: %s", result)
    return result
