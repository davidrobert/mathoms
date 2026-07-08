"""Cache Redis para fiscal/market — stateless ADR-111, falha aberta sem Redis (A7.2b · ADR-135)."""

from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

_FISCAL_TTL_SECONDS = 3600  # 1h fallback
_MARKET_TTL_SECONDS = 86400 * 30  # 30 dias (immutable, pode crescer)


# ---------------------------------------------------------------------------
# Cache keys
# ---------------------------------------------------------------------------


def fiscal_cache_key(year: int) -> str:
    return f"fiscal:y={year}"


def market_cache_key(pair: str, observed_at: date) -> str:
    return f"market:p={pair}:d={observed_at.isoformat()}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_cached_fiscal(year: int) -> dict[str, Any] | None:
    """Lê row de ``fiscal_parameters`` cacheada por ano. ``None`` em miss."""
    raw = _redis_get(fiscal_cache_key(year))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as exc:
        logger.warning("fiscal cache parse failed: %s", exc)
        return None


def store_fiscal_cache(year: int, payload: dict[str, Any]) -> None:
    _redis_set(fiscal_cache_key(year), json.dumps(payload), _FISCAL_TTL_SECONDS)


def invalidate_fiscal(year: int) -> None:
    """Invalidação ativa (consumir em evento ``fiscal_parameter.published``)."""
    _redis_delete(fiscal_cache_key(year))


def get_cached_market_rate(pair: str, observed_at: date) -> Decimal | None:
    raw = _redis_get(market_cache_key(pair, observed_at))
    if raw is None:
        return None
    try:
        return Decimal(raw)
    except Exception as exc:
        logger.warning("market cache parse failed: %s", exc)
        return None


def store_market_rate_cache(pair: str, observed_at: date, rate: Decimal) -> None:
    _redis_set(market_cache_key(pair, observed_at), str(rate), _MARKET_TTL_SECONDS)


def invalidate_market_rate(pair: str, observed_at: date) -> None:
    _redis_delete(market_cache_key(pair, observed_at))


# ---------------------------------------------------------------------------
# Redis primitives — falha aberta
# ---------------------------------------------------------------------------


def _redis_get(key: str) -> str | None:
    client = _get_redis_safe()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception as exc:
        logger.warning("redis GET failed for %s: %s", key, exc)
        return None


def _redis_set(key: str, value: str, ttl_seconds: int) -> None:
    client = _get_redis_safe()
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl_seconds)
    except Exception as exc:
        logger.warning("redis SET failed for %s: %s", key, exc)


def _redis_delete(key: str) -> None:
    client = _get_redis_safe()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:
        logger.warning("redis DEL failed for %s: %s", key, exc)


def _get_redis_safe():
    try:
        from backend.app.services.pipeline.events import _get_redis

        return _get_redis()
    except Exception:
        return None
