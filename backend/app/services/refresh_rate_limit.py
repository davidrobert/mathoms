"""Rate limit em /auth/refresh por família (detecta replay/loop antes da
reuse-detection) e por IP (anti-enumeration de family_id) — mesmo padrão
Redis fail-open de ``register_rate_limit`` (ADR-111, nunca em memória)."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_KEY_PREFIX = "mathoms:auth:refresh_rate"
_DEFAULT_FAMILY_LIMIT_PER_MIN = 5
_DEFAULT_IP_LIMIT_PER_MIN = 20
_TTL_S = 60


def _resolve_limit(env_var: str, default: int) -> int:
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _resolve_client():
    try:
        from backend.app.services.events import _get_redis

        return _get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.warning("refresh_rate_limit: Redis unavailable: %s", exc)
        return None


def _incr_and_check(client, key: str, limit: int) -> tuple[bool, int]:
    new_count = client.incr(key)
    if new_count == 1:
        client.expire(key, _TTL_S)
    if new_count > limit:
        ttl = client.ttl(key)
        return False, max(1, int(ttl) if ttl and ttl > 0 else _TTL_S)
    return True, 0


def check_refresh_rate(
    ip: Optional[str] = None, family_id: Optional[str] = None
) -> tuple[bool, int]:
    """Retorna ``(allowed, retry_after_s)``. Falha aberta sem Redis/limite ≤0."""
    family_limit = _resolve_limit(
        "MATHOMS_REFRESH_RATE_LIMIT_FAMILY_PER_MIN", _DEFAULT_FAMILY_LIMIT_PER_MIN
    )
    ip_limit = _resolve_limit("MATHOMS_REFRESH_RATE_LIMIT_IP_PER_MIN", _DEFAULT_IP_LIMIT_PER_MIN)
    client = _resolve_client()
    if client is None:
        return True, 0
    try:
        return _check_both(client, ip, family_id, ip_limit, family_limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("refresh_rate_limit: backend error: %s", exc)
        return True, 0


def _check_both(client, ip, family_id, ip_limit, family_limit) -> tuple[bool, int]:
    if family_id and family_limit > 0:
        allowed, retry = _incr_and_check(client, f"{_KEY_PREFIX}:fam:{family_id}", family_limit)
        if not allowed:
            return False, retry
    if ip and ip_limit > 0:
        return _incr_and_check(client, f"{_KEY_PREFIX}:ip:{ip}", ip_limit)
    return True, 0
