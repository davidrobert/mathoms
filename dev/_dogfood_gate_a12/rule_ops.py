"""Operações de regra: preview, estimate, create — wrappers ao service sync."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

from backend.app.application.categorization import (
    rule_management_service,
    rule_preview_service,
)
from backend.app.application.categorization._caps import SYNC_APPLY_THRESHOLD
from backend.app.core.database import SyncSessionLocal
from backend.app.models.workspace import Workspace
from backend.app.services.transaction_service import load_transactions
from dev._dogfood_gate_a12.types import RuleResult


def _storage_root() -> Path:
    return Path(os.environ["MATHOMS_STORAGE_ROOT"])


@contextmanager
def sync_db_ctx():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


def load_txs(ws_id: str) -> list:
    return load_transactions(ws_id, str(_storage_root() / ws_id))


def ws_row(sync_db, ws_id: str) -> Workspace:
    return sync_db.execute(select(Workspace).where(Workspace.id == ws_id)).scalar_one()


def run_preview(*, ws_id: str, keyword: str, target_category: str, detector) -> Any:
    transactions = load_txs(ws_id)
    with sync_db_ctx() as sync_db:
        return rule_preview_service.preview_rule(
            workspace_id=ws_id,
            keyword=keyword,
            target_category=target_category,
            period_window=None,
            transactions=transactions,
            db=sync_db,
            detector=detector,
            soft_cap_reached=rule_management_service.soft_cap_reached(
                workspace_id=ws_id, db=sync_db
            ),
        )


def _capture_preview(result: RuleResult, preview) -> None:
    result.preview_matches_total = preview.matches_total
    result.preview_in_closed_months = preview.matches_in_closed_months
    result.preview_with_manual_override = preview.matches_with_manual_override
    result.preview_blocked_internal_transfers = preview.matches_blocked_internal_transfers
    result.preview_warnings = [w.code for w in preview.warnings]
    result.preview_requires_confirmation = preview.requires_user_confirmation


def _mark_async_excluded(result: RuleResult, estimate: int) -> None:
    result.create_async_path = True
    result.create_status = "async_path_excluded"
    result.error_message = (
        f"matches estimados {estimate} > {SYNC_APPLY_THRESHOLD}; "
        f"path async não exercitado neste gate (requer Celery worker)."
    )


def _call_create_rule(
    *, ws_id: str, user_id: str, keyword: str, target_category: str, detector, sync_db
):
    return rule_management_service.create_rule(
        workspace=ws_row(sync_db, ws_id),
        keyword=keyword,
        target_category=target_category,
        priority=100,
        user_id=user_id,
        detector=detector,
        transactions=load_txs(ws_id),
        db=sync_db,
    )


def _capture_create_error(result: RuleResult, exc: Exception) -> None:
    if isinstance(exc, rule_management_service.HardCapExceededError):
        result.create_status = "cap"
        result.error_message = f"hard_cap_exceeded current={exc.current} limit={exc.limit}"
        return
    if isinstance(exc, rule_management_service.RuleAlreadyExistsError):
        result.create_status = "conflict"
        result.error_message = f"rule_already_exists existing_rule_id={exc.existing_rule_id}"
        return
    if isinstance(exc, rule_management_service.ApplyTooLargeError):
        result.create_status = "async_required"
        result.error_message = f"apply_too_large_for_sync expected={exc.expected_overrides}"
        return
    result.create_status = "error"
    result.error_message = f"{type(exc).__name__}: {exc}"


def _try_sync_create(
    *, ws_id: str, user_id: str, keyword: str, target_category: str, detector, result: RuleResult
) -> None:
    with sync_db_ctx() as sync_db:
        try:
            response = _call_create_rule(
                ws_id=ws_id,
                user_id=user_id,
                keyword=keyword,
                target_category=target_category,
                detector=detector,
                sync_db=sync_db,
            )
            result.create_status = "ok"
            result.create_applied_count = response.applied_count
            result.rule_id = response.id
        except Exception as exc:  # noqa: BLE001 — capture domain + fallback errors
            _capture_create_error(result, exc)


@dataclass
class _RuleCtx:
    """Args bundle p/ attempt_create_rule sub-helpers (R9 ISP)."""

    ws_id: str
    user_id: str
    keyword: str
    target_category: str
    detector: Any


def _do_preview(ctx: _RuleCtx, result: RuleResult) -> None:
    preview = run_preview(
        ws_id=ctx.ws_id,
        keyword=ctx.keyword,
        target_category=ctx.target_category,
        detector=ctx.detector,
    )
    _capture_preview(result, preview)


def _estimate(ctx: _RuleCtx) -> int:
    return rule_management_service.estimate_apply_matches(
        keyword=ctx.keyword, target_category=ctx.target_category, transactions=load_txs(ctx.ws_id)
    )


def _sync_create_path(ctx: _RuleCtx, result: RuleResult) -> None:
    _try_sync_create(
        ws_id=ctx.ws_id,
        user_id=ctx.user_id,
        keyword=ctx.keyword,
        target_category=ctx.target_category,
        detector=ctx.detector,
        result=result,
    )


def attempt_create_rule(
    *, ws_id: str, user_id: str, keyword: str, target_category: str, detector
) -> RuleResult:
    """Preview → estimate → sync/async → create. Captura erros tipados."""
    ctx = _RuleCtx(ws_id, user_id, keyword, target_category, detector)
    result = RuleResult(keyword=keyword, target_category=target_category)
    _do_preview(ctx, result)
    estimate = _estimate(ctx)
    result.create_estimated_matches = estimate
    if estimate > SYNC_APPLY_THRESHOLD:
        _mark_async_excluded(result, estimate)
        return result
    _sync_create_path(ctx, result)
    return result


__all__ = ["attempt_create_rule", "load_txs", "run_preview", "sync_db_ctx", "ws_row"]
