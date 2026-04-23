"""Fixtures locais ao slice internal_ops."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def audit_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redireciona `append_audit` para arquivo temporário do teste."""
    log_path = tmp_path / "internal_ops_audit.log"
    from backend.app.services.internal_ops import audit as audit_mod

    monkeypatch.setattr(audit_mod, "audit_log_path", lambda: log_path)
    return log_path
