"""Testes da camada de auth do console interno."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import bcrypt
import pytest
from fastapi import HTTPException

from backend.app.core import internal_ops_auth as ops_auth
from backend.app.core.internal_ops_auth import (
    InternalOperator,
    InternalOpsConfigError,
    InternalOpsPrincipal,
    create_session_token,
    decode_session_token,
    load_operators,
    require_internal_operator,
    verify_operator_password,
)


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


@pytest.fixture
def ops_yaml(tmp_path: Path) -> Path:
    yaml_path = tmp_path / "operators.yaml"
    yaml_path.write_text(
        "operators:\n"
        f"  - username: alice\n    hashed_password: '{_hash('AlicePw1!')}'\n    role: superadmin\n"
        f"  - username: bob\n    hashed_password: '{_hash('BobPw1!')}'\n",
        encoding="utf-8",
    )
    return yaml_path


@pytest.fixture(autouse=True)
def ops_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATHOMS_INTERNAL_OPS_SESSION_SECRET", "test-session-secret-distinct")


def test_load_operators_ok(ops_yaml: Path) -> None:
    ops = load_operators(path=ops_yaml)
    assert set(ops) == {"alice", "bob"}
    assert ops["alice"].role == "superadmin"
    assert ops["bob"].role == "ops"


def test_load_operators_duplicate(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        f"operators:\n  - username: a\n    hashed_password: '{_hash('x')}'\n"
        f"  - username: a\n    hashed_password: '{_hash('y')}'\n",
        encoding="utf-8",
    )
    with pytest.raises(InternalOpsConfigError, match="duplicado"):
        load_operators(path=bad)


def test_load_operators_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InternalOpsConfigError, match="não encontrado"):
        load_operators(path=tmp_path / "nope.yaml")


def test_verify_operator_password(ops_yaml: Path) -> None:
    ops = load_operators(path=ops_yaml)
    assert verify_operator_password(ops["alice"], "AlicePw1!")
    assert not verify_operator_password(ops["alice"], "wrong")


def test_session_roundtrip() -> None:
    p = InternalOpsPrincipal(username="alice", role="superadmin")
    token = create_session_token(p)
    decoded = decode_session_token(token)
    assert decoded == p


def test_session_rejects_client_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.core.config import settings

    monkeypatch.setenv("MATHOMS_INTERNAL_OPS_SESSION_SECRET", settings.SECRET_KEY)
    with pytest.raises(InternalOpsConfigError, match="não pode igualar"):
        create_session_token(InternalOpsPrincipal(username="x", role="ops"))


def test_session_rejects_unset_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MATHOMS_INTERNAL_OPS_SESSION_SECRET", raising=False)
    with pytest.raises(InternalOpsConfigError, match="unset"):
        create_session_token(InternalOpsPrincipal(username="x", role="ops"))


def test_session_expired() -> None:
    p = InternalOpsPrincipal(username="alice", role="ops")
    token = create_session_token(p, expires_delta=timedelta(seconds=-1))
    assert decode_session_token(token) is None


def test_session_wrong_scope() -> None:
    from jose import jwt

    # Token com scope diferente — rejeitado.
    secret = "test-session-secret-distinct"
    token = jwt.encode(
        {"sub": "alice", "role": "ops", "scope": "client"}, secret, algorithm="HS256"
    )
    assert decode_session_token(token) is None


@pytest.mark.asyncio
async def test_require_internal_operator_no_session() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_internal_operator(ops_session=None, authorization=None)
    assert exc.value.status_code == 401
    assert exc.value.detail == "no_session"


@pytest.mark.asyncio
async def test_require_internal_operator_invalid_session() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_internal_operator(ops_session="garbage", authorization=None)
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid_session"


@pytest.mark.asyncio
async def test_require_internal_operator_cookie_ok() -> None:
    token = create_session_token(InternalOpsPrincipal(username="alice", role="ops"))
    principal = await require_internal_operator(ops_session=token, authorization=None)
    assert principal.username == "alice"


@pytest.mark.asyncio
async def test_require_internal_operator_bearer_ok() -> None:
    token = create_session_token(InternalOpsPrincipal(username="bob", role="ops"))
    principal = await require_internal_operator(ops_session=None, authorization=f"Bearer {token}")
    assert principal.username == "bob"


def test_client_token_rejected() -> None:
    """Token assinado com SECRET_KEY do cliente não é aceito no console interno."""
    from backend.app.core.security import create_access_token

    client_token = create_access_token("some-user-id", token_version=0)
    assert decode_session_token(client_token) is None


def test_principal_actor_format() -> None:
    p = InternalOpsPrincipal(username="alice", role="ops")
    assert p.actor == "ops:alice"
