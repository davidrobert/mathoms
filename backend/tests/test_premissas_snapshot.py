"""F11.6b — `build_premissas_snapshot_sync` (hash goals.json + metas ativas)."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.app.services.premissas_snapshot import build_premissas_snapshot_sync


@pytest.fixture
def mock_db_empty_goals() -> MagicMock:
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    return db


def test_snapshot_none_when_no_goals_file_and_no_active_goals(
    tmp_path: Path, mock_db_empty_goals: MagicMock
):
    assert (
        build_premissas_snapshot_sync("ws-1", tmp_path, mock_db_empty_goals) is None
    )


def test_snapshot_includes_goals_json_sha256(
    tmp_path: Path, mock_db_empty_goals: MagicMock
):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "goals.json").write_text('{"x": 1}', encoding="utf-8")
    out = build_premissas_snapshot_sync("ws-1", tmp_path, mock_db_empty_goals)
    assert out is not None
    assert out["schema"] == 1
    assert out["goals_json_sha256"] is not None
    assert len(out["goals_json_sha256"]) == 64
    assert out["active_goals"] == []


def test_snapshot_includes_active_goals_without_goals_file(
    tmp_path: Path,
):
    g1 = MagicMock()
    g1.type = "INDEPENDENCIA_FINANCEIRA"
    g1.id = "goal-1"
    g1.effective_from = datetime(2026, 1, 15, tzinfo=timezone.utc)

    db = MagicMock()
    db.scalars.return_value.all.return_value = [g1]

    out = build_premissas_snapshot_sync("ws-1", tmp_path, db)
    assert out is not None
    assert out["goals_json_sha256"] is None
    assert len(out["active_goals"]) == 1
    assert out["active_goals"][0]["type"] == "INDEPENDENCIA_FINANCEIRA"
    assert out["active_goals"][0]["id"] == "goal-1"
    assert "2026-01-15" in out["active_goals"][0]["effective_from"]
