"""Fixtures de teste para /admin/* routes."""

from __future__ import annotations

from pathlib import Path

import bcrypt
import pytest
import pytest_asyncio


@pytest.fixture
def admin_ui_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "INTERNAL_OPS_UI_ENABLED", True)
    monkeypatch.setenv("MATHOMS_INTERNAL_OPS_SESSION_SECRET", "test-admin-secret-ABC123")


@pytest.fixture
def ops_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    yaml_path = tmp_path / "operators.yaml"
    hashed_alice = bcrypt.hashpw(b"AliceSuper!Pw1", bcrypt.gensalt()).decode()
    hashed_bob = bcrypt.hashpw(b"BobOpsPw123!", bcrypt.gensalt()).decode()
    yaml_path.write_text(
        "operators:\n"
        f"  - username: alice\n    hashed_password: '{hashed_alice}'\n    role: superadmin\n"
        f"  - username: bob\n    hashed_password: '{hashed_bob}'\n    role: ops\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MATHOMS_INTERNAL_OPERATORS_YAML", str(yaml_path))
    return yaml_path


@pytest.fixture
def audit_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from backend.app.services.internal_ops import audit as audit_mod

    log_path = tmp_path / "internal_ops_audit.log"
    monkeypatch.setattr(audit_mod, "audit_log_path", lambda: log_path)
    return log_path


@pytest_asyncio.fixture
async def ops_session_token_superadmin(admin_ui_enabled, ops_yaml, audit_path, client):
    """Autentica como superadmin e devolve o token de cookie."""
    resp = await client.post(
        "/admin/login", json={"username": "alice", "password": "AliceSuper!Pw1"}
    )
    assert resp.status_code == 200, resp.text
    cookie = resp.cookies.get("ops_session")
    assert cookie
    return cookie


@pytest_asyncio.fixture
async def ops_session_token_ops(admin_ui_enabled, ops_yaml, audit_path, client):
    resp = await client.post("/admin/login", json={"username": "bob", "password": "BobOpsPw123!"})
    assert resp.status_code == 200, resp.text
    return resp.cookies.get("ops_session")
