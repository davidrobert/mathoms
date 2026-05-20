"""Password hashing and JWT token utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from backend.app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    token_version: int = 0,
) -> str:
    """Cria JWT. `token_version` é o valor vigente de `User.token_version` no
    momento da criação — ao ser incrementado (ex: remoção de membership),
    tokens stale ficam inválidos em `decode_access_token`."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": subject, "exp": expire, "tv": token_version}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Compat shim — retorna só o subject. Use `decode_access_token_payload`
    quando precisar de outros claims (ex: `tv`)."""
    payload = decode_access_token_payload(token)
    return payload.get("sub") if payload else None


def decode_access_token_payload(token: str) -> Optional[dict]:
    """Decodifica o JWT retornando o payload completo (sub, exp, tv).
    None se assinatura inválida ou expirado."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError:
        return None
