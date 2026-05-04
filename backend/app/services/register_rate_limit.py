"""Rate limit IP-based em /auth/register para prevenir abuse + email enumeration."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_KEY_PREFIX = "mathoms:auth:register_rate"
_DEFAULT_LIMIT_PER_HOUR = 10
_TTL_S = 3600


def _resolve_limit() -> int:
    raw = os.environ.get("MATHOMS_REGISTER_RATE_LIMIT_PER_HOUR")
    if not raw:
        return _DEFAULT_LIMIT_PER_HOUR
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_LIMIT_PER_HOUR


def _resolve_client():
    """Reusa o singleton Redis do events.py — Pub/Sub já cuida de retry."""
    try:
        from backend.app.services.events import _get_redis

        return _get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.warning("register_rate_limit: Redis unavailable: %s", exc)
        return None


def _incr_and_check(client, ip: str) -> tuple[bool, int]:
    """INCR + EXPIRE no Redis; retorna (allowed, retry_after_s)."""
    key = f"{_KEY_PREFIX}:{ip}"
    new_count = client.incr(key)
    if new_count == 1:
        client.expire(key, _TTL_S)
    if new_count > _resolve_limit():
        ttl = client.ttl(key)
        return False, max(1, int(ttl) if ttl and ttl > 0 else _TTL_S)
    return True, 0


def check_register_rate(ip: Optional[str] = None) -> tuple[bool, int]:
    """Retorna (allowed, retry_after_s). Falha aberta sem IP/sem Redis."""
    if not ip:
        return True, 0
    client = _resolve_client()
    if client is None:
        return True, 0
    try:
        return _incr_and_check(client, ip)
    except Exception as exc:  # noqa: BLE001
        logger.warning("register_rate_limit: backend error: %s", exc)
        return True, 0
