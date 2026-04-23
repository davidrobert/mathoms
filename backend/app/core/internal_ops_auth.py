"""Auth isolada do console interno (ADR-116 Decisão 3).

- Operadores definidos em `config/internal_operators.yaml` (gitignored).
- Hash bcrypt; login valida e emite JWT assinado com
  `INTERNAL_OPS_SESSION_SECRET` — variável separada do `SECRET_KEY` do
  cliente; sem fallback.
- JWT carregado via cookie `ops_session` (HttpOnly, SameSite=Strict,
  Path=/admin) ou header `Authorization: Bearer` (para CLI futuro).

Tokens do cliente (`SECRET_KEY`) **nunca** são aceitos aqui, e vice-versa:
segredos distintos garantem isolamento criptográfico.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import bcrypt
import yaml
from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError, jwt

from backend.app.core.config import settings

_ALGORITHM = "HS256"
_SESSION_TTL_MINUTES = 60 * 8  # 8h
_COOKIE_NAME = "ops_session"
_YAML_PATH_ENV = "MATHOMS_INTERNAL_OPERATORS_YAML"
_DEFAULT_YAML = Path(settings.PIPELINE_ROOT) / "config" / "internal_operators.yaml"


class InternalOpsConfigError(RuntimeError):
    """Raised when the operators yaml is missing/malformed or the session
    secret is unset — fail-fast at startup instead of surprising 500s."""


@dataclass(frozen=True)
class InternalOperator:
    username: str
    hashed_password: str
    role: str = "ops"


@dataclass(frozen=True)
class InternalOpsPrincipal:
    """Operador autenticado (ator de audit)."""

    username: str
    role: str

    @property
    def actor(self) -> str:
        return f"ops:{self.username}"


def _session_secret() -> str:
    secret = os.environ.get("MATHOMS_INTERNAL_OPS_SESSION_SECRET", "").strip()
    if not secret:
        raise InternalOpsConfigError(
            "MATHOMS_INTERNAL_OPS_SESSION_SECRET unset — console interno exige secret distinto do SECRET_KEY do cliente (ADR-116)."
        )
    if secret == settings.SECRET_KEY:
        raise InternalOpsConfigError(
            "MATHOMS_INTERNAL_OPS_SESSION_SECRET não pode igualar MATHOMS_SECRET_KEY — isolamento criptográfico quebrado."
        )
    return secret


def _yaml_path() -> Path:
    override = os.environ.get(_YAML_PATH_ENV, "").strip()
    return Path(override) if override else _DEFAULT_YAML


def load_operators(*, path: Path | None = None) -> dict[str, InternalOperator]:
    """Carrega operadores do yaml. Retorna dict username → operator."""
    target = path or _yaml_path()
    if not target.exists():
        raise InternalOpsConfigError(f"Arquivo de operadores internos não encontrado: {target}")
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise InternalOpsConfigError(f"YAML inválido em {target}: {exc}") from exc

    operators_raw = raw.get("operators", [])
    if not isinstance(operators_raw, list):
        raise InternalOpsConfigError(
            f"Campo 'operators' deve ser lista em {target}; achei {type(operators_raw).__name__}"
        )

    out: dict[str, InternalOperator] = {}
    for item in operators_raw:
        if not isinstance(item, dict):
            raise InternalOpsConfigError(f"Entrada inválida em {target}: {item!r}")
        username = str(item.get("username", "")).strip()
        hashed = str(item.get("hashed_password", "")).strip()
        role = str(item.get("role", "ops")).strip() or "ops"
        if not username or not hashed:
            raise InternalOpsConfigError(
                f"Operador sem username/hashed_password em {target}: {item!r}"
            )
        if username in out:
            raise InternalOpsConfigError(f"Username duplicado em {target}: {username}")
        out[username] = InternalOperator(username=username, hashed_password=hashed, role=role)
    return out


def verify_operator_password(op: InternalOperator, password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), op.hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_session_token(
    principal: InternalOpsPrincipal, *, expires_delta: timedelta | None = None
) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=_SESSION_TTL_MINUTES))
    payload: dict[str, Any] = {
        "sub": principal.username,
        "role": principal.role,
        "exp": expire,
        "scope": "internal_ops",
    }
    return jwt.encode(payload, _session_secret(), algorithm=_ALGORITHM)


def decode_session_token(token: str) -> InternalOpsPrincipal | None:
    try:
        payload = jwt.decode(token, _session_secret(), algorithms=[_ALGORITHM])
    except JWTError:
        return None
    if payload.get("scope") != "internal_ops":
        return None
    sub = payload.get("sub")
    role = payload.get("role")
    if not sub or not role:
        return None
    return InternalOpsPrincipal(username=str(sub), role=str(role))


def session_cookie_name() -> str:
    return _COOKIE_NAME


def session_ttl_minutes() -> int:
    return _SESSION_TTL_MINUTES


async def require_internal_operator(
    ops_session: str | None = Cookie(default=None, alias=_COOKIE_NAME),
    authorization: str | None = Header(default=None),
) -> InternalOpsPrincipal:
    """FastAPI dependency — 401 se cookie/header ausente ou inválido.

    Cookie tem precedência (UI); header `Authorization: Bearer` suporta CLI
    e testes.
    """
    token = ops_session
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no_session")
    principal = decode_session_token(token)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session")
    return principal


__all__ = [
    "InternalOpsConfigError",
    "InternalOperator",
    "InternalOpsPrincipal",
    "load_operators",
    "verify_operator_password",
    "create_session_token",
    "decode_session_token",
    "require_internal_operator",
    "session_cookie_name",
    "session_ttl_minutes",
]


# Explicit re-use guard — pulled in by `Depends` users as shorthand
internal_operator_dep = Depends(require_internal_operator)
