"""Testes do Celery task ``apply_rule_retroactive_task`` — idempotência + COUNT pós-fato (ADR-188 PR3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from backend.app.core.database import SyncSessionLocal
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_RULE,
    TransactionOverride,
)
from backend.app.models.workspace import Workspace


def _seed_user_workspace(db) -> tuple[str, str]:
    from backend.app.models.user import User

    user_id = str(uuid.uuid4())
    ws_id = str(uuid.uuid4())
    db.add(
        User(
            id=user_id,
            email=f"u-{user_id[:8]}@test.local",
            hashed_password="x" * 60,
            full_name="Tester",
        )
    )
    db.flush()
    db.add(Workspace(id=ws_id, name="t", family_surname="t", owner_id=user_id))
    db.flush()
    return user_id, ws_id


def _seed_workspace_and_rule(db):
    _, ws_id = _seed_user_workspace(db)
    rule = CategorizationRule(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        keyword="NETFLIX",
        target_category="Lazer",
        priority=100,
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(rule)
    db.commit()
    return ws_id, rule.id


def _make_rule_override(
    *, ws_id: str, rule_id: str, tx_hash: str, deleted: bool = False
) -> TransactionOverride:
    return TransactionOverride(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        transaction_hash=tx_hash,
        original_category="Outros",
        new_category="Lazer",
        source=OVERRIDE_SOURCE_RULE,
        rule_id=rule_id,
        reviewed=True,
        created_at=datetime.now(timezone.utc),
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )


def test_count_applied_overrides_returns_count():
    """``_count_applied_overrides`` retorna count canônico (não soma de bumps)."""
    from backend.app.application.categorization._apply_engine import count_applied_overrides

    with SyncSessionLocal() as db:
        ws_id, rule_id = _seed_workspace_and_rule(db)
        for i in range(3):
            db.add(_make_rule_override(ws_id=ws_id, rule_id=rule_id, tx_hash=f"hash-{i}"))
        db.commit()
        assert count_applied_overrides(db, ws_id, rule_id) == 3


def test_count_applied_overrides_excludes_deleted():
    """Overrides soft-deleted não contam (ADR-188 §D1)."""
    from backend.app.application.categorization._apply_engine import count_applied_overrides

    with SyncSessionLocal() as db:
        ws_id, rule_id = _seed_workspace_and_rule(db)
        db.add(_make_rule_override(ws_id=ws_id, rule_id=rule_id, tx_hash="active"))
        db.add(_make_rule_override(ws_id=ws_id, rule_id=rule_id, tx_hash="deleted", deleted=True))
        db.commit()
        assert count_applied_overrides(db, ws_id, rule_id) == 1


def test_set_applied_count_does_not_bump_repeatedly():
    """``set_applied_count`` é SETter (não bumper) — idempotente em retry."""
    from backend.app.application.categorization.rule_management_service import set_applied_count

    with SyncSessionLocal() as db:
        ws_id, rule_id = _seed_workspace_and_rule(db)
        set_applied_count(rule_id=rule_id, applied=42, db=db)
        db.commit()
        rule = db.get(CategorizationRule, rule_id)
        assert rule.applied_count == 42
        set_applied_count(rule_id=rule_id, applied=42, db=db)
        db.commit()
        db.refresh(rule)
        assert rule.applied_count == 42
        set_applied_count(rule_id=rule_id, applied=7, db=db)
        db.commit()
        db.refresh(rule)
        assert rule.applied_count == 7


def test_apply_task_skips_when_already_completed_idempotent():
    """Retry após `mark_completed` no Redis: task pula execução."""
    from backend.app.tasks.categorization_apply import apply_rule_retroactive_task

    with patch("backend.app.services.rule_apply_state.is_already_completed", return_value=True):
        result = apply_rule_retroactive_task.run("ws-x", "rule-y")
    assert result["status"] == "completed"
    assert result.get("skipped") is True


def test_apply_task_marks_failed_on_exception():
    """Exceção no apply → ``mark_failed`` chamado com mensagem."""
    from backend.app.tasks.categorization_apply import apply_rule_retroactive_task

    with (
        patch("backend.app.services.rule_apply_state.is_already_completed", return_value=False),
        patch(
            "backend.app.tasks.categorization_apply._do_apply",
            side_effect=RuntimeError("boom"),
        ),
        patch("backend.app.services.rule_apply_state.mark_failed") as m_failed,
    ):
        with pytest.raises(RuntimeError):
            apply_rule_retroactive_task.run("ws-x", "rule-y")
    m_failed.assert_called_once()
    kwargs = m_failed.call_args.kwargs
    assert kwargs["workspace_id"] == "ws-x"
    assert "boom" in kwargs["error"]
