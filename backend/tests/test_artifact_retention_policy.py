"""``ArtifactRetentionPolicy`` + loader (A33.l6 · W6-T05): value object frozen
valida boundary (dias ≥ 1, mode no vocabulário); loader resolve env >
pipeline.json > default com fallback fail-safe (inválido → 180d/dry_run)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.services.artifact_retention import (
    PRUNE_MODE_DELETE,
    PRUNE_MODE_DRY_RUN,
    ArtifactRetentionPolicy,
    load_artifact_retention_policy,
)

_ENV_DAYS = "MATHOMS_ARTIFACT_RETENTION_SUPERSEDED_DAYS"
_ENV_MODE = "MATHOMS_ARTIFACT_PRUNE_MODE"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(_ENV_DAYS, raising=False)
    monkeypatch.delenv(_ENV_MODE, raising=False)


def _patch_config(monkeypatch, section: dict) -> None:
    import scripts.pipeline_common as pc

    monkeypatch.setattr(pc, "load_json_config", lambda name, **kw: {"artifact_retention": section})


def test_defaults_are_conservative(monkeypatch):
    _patch_config(monkeypatch, {})
    policy = load_artifact_retention_policy()
    assert policy.superseded_days == 180
    assert policy.prune_mode == PRUNE_MODE_DRY_RUN
    assert policy.delete_enabled is False


def test_retention_until_adds_superseded_days():
    policy = ArtifactRetentionPolicy(superseded_days=30)
    now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
    assert policy.retention_until(now=now) == now + timedelta(days=30)


def test_invalid_days_raises_with_offending_value():
    with pytest.raises(ValueError, match="superseded_days >= 1, got 0"):
        ArtifactRetentionPolicy(superseded_days=0)


def test_invalid_mode_raises_with_offending_value():
    with pytest.raises(ValueError, match="prune_mode"):
        ArtifactRetentionPolicy(prune_mode="yolo")


def test_env_overrides_pipeline_json(monkeypatch):
    _patch_config(monkeypatch, {"superseded_days": 90, "prune_mode": "dry_run"})
    monkeypatch.setenv(_ENV_DAYS, "7")
    monkeypatch.setenv(_ENV_MODE, "delete")
    policy = load_artifact_retention_policy()
    assert policy.superseded_days == 7
    assert policy.prune_mode == PRUNE_MODE_DELETE
    assert policy.delete_enabled is True


def test_pipeline_json_section_used_without_env(monkeypatch):
    _patch_config(monkeypatch, {"superseded_days": 45, "prune_mode": "delete"})
    policy = load_artifact_retention_policy()
    assert policy.superseded_days == 45
    assert policy.prune_mode == PRUNE_MODE_DELETE


def test_invalid_env_values_fall_back_fail_safe(monkeypatch):
    _patch_config(monkeypatch, {})
    monkeypatch.setenv(_ENV_DAYS, "not-a-number")
    monkeypatch.setenv(_ENV_MODE, "purge-everything")
    policy = load_artifact_retention_policy()
    assert policy.superseded_days == 180
    assert policy.prune_mode == PRUNE_MODE_DRY_RUN


def test_negative_days_fall_back_fail_safe(monkeypatch):
    _patch_config(monkeypatch, {"superseded_days": -5})
    policy = load_artifact_retention_policy()
    assert policy.superseded_days == 180
