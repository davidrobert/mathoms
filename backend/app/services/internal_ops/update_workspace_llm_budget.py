"""Edição do budget LLM mensal de workspace via console interno (A30.l1 · ADR-173)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.models.workspace import Workspace
from backend.app.schemas.admin import WorkspaceLLMBudgetUpdate
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult

_JUMP_ALERT_FACTOR = Decimal("3")

_budget_change_log = get_logger("internal_ops.budget_change")


async def _load_workspace(db: AsyncSession, workspace_id: str) -> Workspace | None:
    return (
        await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()


def _audit(
    db: AsyncSession,
    *,
    actor: str,
    ws_id: str,
    previous: str | None,
    current: str | None,
    remove_cap: bool,
) -> None:
    # Hard-fail por contrato (A30.l1): falha do sink = falha da operação.
    append_audit(
        AuditRecord(
            action="workspace.update_llm_budget",
            actor=actor,
            target_type="workspace",
            target_id=ws_id,
            details={"previous": previous, "current": current, "remove_cap": remove_cap},
        ),
        db,
    )


def _is_suspicious_jump(previous: Decimal | None, current: Decimal | None) -> bool:
    if previous is None or current is None or previous <= 0:
        return False
    return current > previous * _JUMP_ALERT_FACTOR


def _log_change(
    *, actor: str, ws_id: str, previous: Decimal | None, current: Decimal | None
) -> None:
    jump = _is_suspicious_jump(previous, current)
    log = _budget_change_log.warning if (jump or current is None) else _budget_change_log.info
    log(
        "llm budget change",
        extra={
            "workspace_id": ws_id,
            "actor": actor,
            "previous_usd": _opt_str(previous),
            "current_usd": _opt_str(current),
            "uncapped": current is None,
            "suspicious_jump": jump,
        },
    )


def _opt_str(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _record_change(
    db: AsyncSession,
    actor: str,
    ws_id: str,
    previous: Decimal | None,
    current: Decimal | None,
    remove_cap: bool,
) -> None:
    _audit(
        db,
        actor=actor,
        ws_id=ws_id,
        previous=_opt_str(previous),
        current=_opt_str(current),
        remove_cap=remove_cap,
    )
    _log_change(actor=actor, ws_id=ws_id, previous=previous, current=current)


async def _apply_cap(
    db: AsyncSession, workspace: Workspace, current: Decimal | None
) -> Decimal | None:
    previous = workspace.monthly_llm_budget_usd
    workspace.monthly_llm_budget_usd = current
    await db.flush()
    return None if previous is None else Decimal(previous)


def _success(
    ws_id: str, previous: Decimal | None, current: Decimal | None, remove_cap: bool
) -> OpResult:
    return OpResult.success(
        workspace_id=ws_id,
        previous_budget_usd=_opt_str(previous),
        monthly_budget_usd=_opt_str(current),
        remove_cap=remove_cap,
    )


async def update_workspace_llm_budget(
    db: AsyncSession,
    workspace_id: str,
    *,
    actor: str,
    payload: WorkspaceLLMBudgetUpdate,
) -> OpResult:
    """Define ou remove o cap mensal (`NULL` só via `remove_cap` explícito)."""
    workspace = await _load_workspace(db, workspace_id)
    if workspace is None:
        return OpResult.failure("workspace_not_found", workspace_id=workspace_id)
    current = None if payload.remove_cap else payload.cap_usd
    previous = await _apply_cap(db, workspace, current)
    _record_change(db, actor, workspace_id, previous, current, payload.remove_cap)
    return _success(workspace_id, previous, current, payload.remove_cap)
