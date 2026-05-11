"""Celery task: apply retroativo async de ``CategorizationRule`` — idempotente via Redis + COUNT pós-fato (ADR-188 PR3)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select

from backend.app.application.categorization.rule_management_service import (
    apply_retroactive_async_safe,
    set_applied_count,
)
from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.workspace import Workspace
from backend.app.repositories.config_blob_repository import ConfigBlobRepository
from backend.app.services import rule_apply_state
from backend.app.services.config_defaults import ConfigDefaultsLoader
from backend.app.services.transaction_service import load_transactions
from backend.app.worker import celery_app

logger = logging.getLogger("categorization_apply_task")


def _load_transactions_for(workspace_id: str) -> list:
    """Carrega transações E4 — mesma fonte usada pelo endpoint sync."""
    return load_transactions(workspace_id, str(settings.STORAGE_ROOT / workspace_id))


def _resolve_detector_sync(workspace_id: str, db) -> "object":
    """Resolve detector via async-bridge — fallback p/ empty detector em falha."""
    import asyncio

    from backend.app.services.transfer_detector_resolver import (
        resolve_internal_transfer_detector,
    )

    repo = ConfigBlobRepository(db)
    defaults = ConfigDefaultsLoader()
    try:
        return asyncio.run(
            resolve_internal_transfer_detector(workspace_id, repo=repo, defaults=defaults)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("apply_task.detector_fallback workspace=%s err=%s", workspace_id, exc)
        from backend.app.application.categorization.rule_preview_service import (
            empty_detector,
        )

        return empty_detector()


def _fetch_rule(db, rule_id: str, workspace_id: str) -> Optional[CategorizationRule]:
    stmt = select(CategorizationRule).where(
        CategorizationRule.id == rule_id,
        CategorizationRule.workspace_id == workspace_id,
        CategorizationRule.deleted_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


def _fetch_workspace(db, workspace_id: str) -> Optional[Workspace]:
    return db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalar_one_or_none()


def _do_apply(*, workspace_id: str, rule_id: str) -> int:
    """Núcleo de aplicação — sessão própria, commit ao fim. Retorna applied_count."""
    transactions = _load_transactions_for(workspace_id)
    with SyncSessionLocal() as db:
        rule = _fetch_rule(db, rule_id, workspace_id)
        ws = _fetch_workspace(db, workspace_id)
        if rule is None or ws is None:
            logger.warning(
                "apply_task.missing_rule_or_workspace ws=%s rule=%s", workspace_id, rule_id
            )
            return 0
        detector = _resolve_detector_sync(workspace_id, db)
        applied = apply_retroactive_async_safe(
            workspace_id=workspace_id,
            rule=rule,
            detector=detector,
            transactions=transactions,
            db=db,
        )
        set_applied_count(rule_id=rule_id, applied=applied, db=db)
        db.commit()
        return applied


def _skipped_result(workspace_id: str, rule_id: str) -> dict:
    return {
        "status": "completed",
        "applied_count": 0,
        "rule_id": rule_id,
        "workspace_id": workspace_id,
        "skipped": True,
    }


def _completed_result(workspace_id: str, rule_id: str, applied: int) -> dict:
    return {
        "status": "completed",
        "applied_count": applied,
        "rule_id": rule_id,
        "workspace_id": workspace_id,
    }


@celery_app.task(
    name="categorization.apply_rule_retroactive",
    bind=True,
    max_retries=2,
    acks_late=True,
    time_limit=900,
    soft_time_limit=840,
)
def apply_rule_retroactive_task(self, workspace_id: str, rule_id: str) -> dict:
    """Aplica regra retroativamente — idempotente via Redis ``is_already_completed`` skip."""
    if rule_apply_state.is_already_completed(workspace_id=workspace_id, rule_id=rule_id):
        logger.info("apply_task.already_completed ws=%s rule=%s skipping", workspace_id, rule_id)
        return _skipped_result(workspace_id, rule_id)
    try:
        applied = _do_apply(workspace_id=workspace_id, rule_id=rule_id)
    except Exception as exc:
        logger.exception("apply_task.failed ws=%s rule=%s err=%s", workspace_id, rule_id, exc)
        rule_apply_state.mark_failed(workspace_id=workspace_id, rule_id=rule_id, error=str(exc))
        raise
    rule_apply_state.mark_completed(
        workspace_id=workspace_id, rule_id=rule_id, applied_count=applied
    )
    logger.info("apply_task.completed ws=%s rule=%s applied=%d", workspace_id, rule_id, applied)
    return _completed_result(workspace_id, rule_id, applied)
