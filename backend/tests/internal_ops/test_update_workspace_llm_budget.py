"""``update_workspace_llm_budget`` — cap mensal editável com audit hard-fail (A30.l1)."""

from __future__ import annotations

import importlib
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.schemas.admin import MAX_SETTABLE_BUDGET_USD, WorkspaceLLMBudgetUpdate
from backend.app.services.internal_ops import update_workspace_llm_budget
from backend.app.services.internal_ops.audit import read_audit
from backend.tests.factories.builders import make_workspace


def _payload(**kwargs) -> WorkspaceLLMBudgetUpdate:
    return WorkspaceLLMBudgetUpdate(**kwargs)


@pytest.mark.asyncio
async def test_set_cap_happy_path(db, audit_path: Path) -> None:
    ws = await make_workspace(db)
    result = await update_workspace_llm_budget(
        db, ws.id, actor="ops@test", payload=_payload(cap_usd="20")
    )
    assert result.ok
    assert result.details["monthly_budget_usd"] == "20.00"
    assert result.details["previous_budget_usd"] == "5.00"
    await db.refresh(ws)
    assert ws.monthly_llm_budget_usd == Decimal("20.00")


@pytest.mark.asyncio
async def test_remove_cap_explicit(db, audit_path: Path) -> None:
    ws = await make_workspace(db)
    result = await update_workspace_llm_budget(
        db, ws.id, actor="ops@test", payload=_payload(remove_cap=True)
    )
    assert result.ok
    assert result.details["monthly_budget_usd"] is None
    await db.refresh(ws)
    assert ws.monthly_llm_budget_usd is None


@pytest.mark.asyncio
async def test_workspace_not_found(db, audit_path: Path) -> None:
    result = await update_workspace_llm_budget(
        db, "nope", actor="ops@test", payload=_payload(cap_usd="10")
    )
    assert not result.ok
    assert result.error == "workspace_not_found"
    assert read_audit(path=audit_path) == []


@pytest.mark.asyncio
async def test_audit_written_with_literal_values(db, audit_path: Path) -> None:
    ws = await make_workspace(db)
    await update_workspace_llm_budget(
        db, ws.id, actor="ops@test", payload=_payload(cap_usd="12.50")
    )
    entries = read_audit(path=audit_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["action"] == "workspace.update_llm_budget"
    assert entry["target_id"] == ws.id
    assert entry["details"] == {"previous": "5.00", "current": "12.50", "remove_cap": False}


@pytest.mark.asyncio
async def test_audit_sink_failure_fails_operation(db, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = importlib.import_module("backend.app.services.internal_ops.update_workspace_llm_budget")

    def _boom(record) -> None:
        raise OSError("sink indisponível")

    monkeypatch.setattr(mod, "append_audit", _boom)
    ws = await make_workspace(db)
    with pytest.raises(OSError):
        await update_workspace_llm_budget(
            db, ws.id, actor="ops@test", payload=_payload(cap_usd="10")
        )


class _RecordingLogger:
    """Recorder imune a propagate=False do namespace mathoms.* (padrão de
    tests/test_llm_budget_service.py)."""

    def __init__(self) -> None:
        self.warnings: list[dict] = []
        self.infos: list[dict] = []

    def warning(self, msg: str, *args, extra=None, **kwargs) -> None:
        self.warnings.append(extra or {})

    def info(self, msg: str, *args, extra=None, **kwargs) -> None:
        self.infos.append(extra or {})


@pytest.mark.asyncio
async def test_suspicious_jump_emits_warning(
    db, audit_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = importlib.import_module("backend.app.services.internal_ops.update_workspace_llm_budget")

    recorder = _RecordingLogger()
    monkeypatch.setattr(mod, "_budget_change_log", recorder)
    ws = await make_workspace(db)
    await update_workspace_llm_budget(db, ws.id, actor="ops@test", payload=_payload(cap_usd="100"))
    assert len(recorder.warnings) == 1
    assert recorder.warnings[0]["suspicious_jump"] is True


@pytest.mark.asyncio
async def test_moderate_change_logs_info(
    db, audit_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = importlib.import_module("backend.app.services.internal_ops.update_workspace_llm_budget")

    recorder = _RecordingLogger()
    monkeypatch.setattr(mod, "_budget_change_log", recorder)
    ws = await make_workspace(db)
    await update_workspace_llm_budget(db, ws.id, actor="ops@test", payload=_payload(cap_usd="10"))
    assert recorder.warnings == []
    assert len(recorder.infos) == 1
    assert recorder.infos[0]["suspicious_jump"] is False


def test_reject_negative() -> None:
    with pytest.raises(ValidationError):
        _payload(cap_usd="-1")


def test_reject_nan() -> None:
    with pytest.raises(ValidationError):
        _payload(cap_usd="nan")


def test_reject_above_sanity_cap() -> None:
    with pytest.raises(ValidationError, match="teto de sanidade"):
        _payload(cap_usd=str(MAX_SETTABLE_BUDGET_USD + 1))


def test_reject_null_without_remove_cap() -> None:
    with pytest.raises(ValidationError, match="remove_cap"):
        _payload()


def test_reject_cap_with_remove_cap() -> None:
    with pytest.raises(ValidationError):
        _payload(cap_usd="10", remove_cap=True)


def test_cap_quantized_to_cents() -> None:
    assert _payload(cap_usd="19.999").cap_usd == Decimal("20.00")
