"""Use cases ``get_feature_flags`` / ``set_feature_flag`` (A6e.4 · ADR-074)."""

from __future__ import annotations

import pytest

from backend.app.application.base import ValidationError
from backend.app.application.feature_flag import (
    FlagUpdateCommand,
    get_feature_flags,
    set_feature_flag,
)
from backend.app.services import feature_flags_service
from backend.tests import factories


@pytest.mark.asyncio
async def test_get_returns_defaults_for_new_workspace(db):
    ws = await factories.make_workspace(db)
    resp = await get_feature_flags(ws.id, db=db)
    assert resp.flags == feature_flags_service.DEFAULTS


@pytest.mark.asyncio
async def test_set_persists_override_and_commits(db):
    ws = await factories.make_workspace(db)
    resp = await set_feature_flag(
        ws.id, "tasks_v2_enabled", FlagUpdateCommand(enabled=False), db=db
    )
    assert resp.flags["tasks_v2_enabled"] is False
    assert resp.flags["report_tasks_snapshot_enabled"] is True


@pytest.mark.asyncio
async def test_set_raises_validation_error_on_unknown_flag(db):
    ws = await factories.make_workspace(db)
    with pytest.raises(ValidationError):
        await set_feature_flag(
            ws.id, "flag_inexistente", FlagUpdateCommand(enabled=True), db=db
        )
