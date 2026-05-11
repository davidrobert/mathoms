"""Soft + hard cap tests — exercita warnings + erro tipado."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.application.categorization import rule_management_service
from backend.app.application.categorization._caps import (
    RULE_HARD_CAP,
    RULE_SOFT_CAP,
)
from backend.app.models.categorization_rule import CategorizationRule
from dev._dogfood_gate_a12.rule_ops import load_txs, run_preview, sync_db_ctx, ws_row
from dev._dogfood_gate_a12.types import GateInvariant


def _count_dummy_rules(sync_db, ws_id: str) -> int:
    rows = (
        sync_db.execute(
            select(CategorizationRule.keyword).where(
                CategorizationRule.workspace_id == ws_id,
                CategorizationRule.keyword.like("DUMMYKW%"),
            )
        )
        .scalars()
        .all()
    )
    return len(rows)


def _make_dummy_rule(ws_id: str, keyword: str) -> CategorizationRule:
    return CategorizationRule(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        keyword=keyword,
        target_category="Outros",
        priority=100,
        enabled=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _seed_dummy_rules(ws_id: str, count: int) -> None:
    with sync_db_ctx() as sync_db:
        offset = _count_dummy_rules(sync_db, ws_id)
        for i in range(count):
            sync_db.add(_make_dummy_rule(ws_id, f"DUMMYKW{offset + i:05d}"))
        sync_db.commit()


def _seed_until_count(ws_id: str, target: int) -> None:
    with sync_db_ctx() as sync_db:
        current = rule_management_service._count_active_rules(sync_db, ws_id)
    needed = max(0, target - current)
    if needed > 0:
        _seed_dummy_rules(ws_id, needed)


def test_soft_cap_warning(ws_id: str, detector) -> GateInvariant:
    """Após RULE_SOFT_CAP regras, preview deve emitir near_soft_cap."""
    _seed_until_count(ws_id, RULE_SOFT_CAP)
    preview = run_preview(
        ws_id=ws_id, keyword="AFTERSOFTCAP", target_category="Outros", detector=detector
    )
    codes = {w.code for w in preview.warnings}
    return GateInvariant(
        code="soft_cap_warning",
        description="Preview emite warning near_soft_cap quando count >= RULE_SOFT_CAP",
        status="PASS" if "near_soft_cap" in codes else "FAIL",
        detail=f"rules ativas após seed: {RULE_SOFT_CAP}; warnings preview: {sorted(codes)}",
    )


def _try_create_overcap(ws_id: str, user_id: str, detector) -> tuple[bool, str]:
    with sync_db_ctx() as sync_db:
        try:
            rule_management_service.create_rule(
                workspace=ws_row(sync_db, ws_id),
                keyword="OVERHARDCAP",
                target_category="Outros",
                priority=100,
                user_id=user_id,
                detector=detector,
                transactions=load_txs(ws_id),
                db=sync_db,
            )
            return False, "create_rule não levantou HardCapExceededError"
        except rule_management_service.HardCapExceededError as exc:
            return True, f"levantou HardCapExceededError current={exc.current} limit={exc.limit}"


def test_hard_cap_block(ws_id: str, user_id: str, detector) -> GateInvariant:
    """Atingindo RULE_HARD_CAP, create deve falhar com hard_cap_exceeded."""
    _seed_until_count(ws_id, RULE_HARD_CAP)
    raised, detail = _try_create_overcap(ws_id, user_id, detector)
    return GateInvariant(
        code="hard_cap_block",
        description=f"create_rule falha com hard_cap_exceeded em count={RULE_HARD_CAP}",
        status="PASS" if raised else "FAIL",
        detail=detail,
    )


__all__ = ["test_hard_cap_block", "test_soft_cap_warning"]
