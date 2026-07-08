"""Cache Redis para resolved categories — invalidação ativa por evento (A7.3 · ADR-137).

Stateless rigoroso (ADR-111): sem ``@lru_cache`` em processo. Falha aberta —
sem Redis, cai no DB. Invalidação por evento (publicada em qualquer write
de override ou bump de ``template_version``) — não por TTL.
Observabilidade (SRE #192): cada read emite ``mathoms.cache.requests``
com ``cache`` + ``result`` (``hit`` | ``miss`` | ``fallback``); SRE
deriva counter RED em Loki/CloudWatch.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.app.core.logging import get_logger

logger = logging.getLogger(__name__)
_cache_metrics = get_logger("cache.requests")

# 24h fallback TTL — invalidation should normally happen on event publish;
# TTL é guarda-redes para o caso (raro) do evento não chegar.
_RESOLVED_TTL_SECONDS = 86400
_TEMPLATE_TTL_SECONDS = 86400 * 30
# 15min TTL para ``latest_template_version`` — valor global, muda raríssimo
# (só em seed Alembic de novo template). TTL curto reduz blast radius de
# bug de invalidação esquecida (SRE follow-up #192); workload de seed é raro,
# read continua barato em miss.
_LATEST_TEMPLATE_VERSION_TTL_SECONDS = 900
_LATEST_TEMPLATE_VERSION_KEY = "categories:latest_template_version"


def _record_cache_event(cache: str, result: str) -> None:
    """Emite log estruturado contável (Grafana Loki/CloudWatch) — ``result`` ∈ {hit, miss, fallback}."""
    _cache_metrics.info("cache request", extra={"cache": cache, "result": result})


def resolved_cache_key(workspace_id: str, template_version: int) -> str:
    return f"categories:ws={workspace_id}:v={template_version}"


def template_cache_key(template_version: int) -> str:
    return f"category_template:v={template_version}"


def get_cached_resolved(workspace_id: str, template_version: int) -> list[dict] | None:
    """Lê lista cacheada de resolved categories. ``None`` em miss/parse-fail."""
    raw, status = _redis_get_with_status(resolved_cache_key(workspace_id, template_version))
    _record_cache_event("resolved_categories", status)
    if raw is None:
        return None
    try:
        return list(json.loads(raw))
    except (ValueError, TypeError) as exc:
        logger.warning("category cache parse failed: %s", exc)
        return None


def store_resolved_cache(workspace_id: str, template_version: int, payload: list[dict]) -> None:
    _redis_set(
        resolved_cache_key(workspace_id, template_version),
        json.dumps(payload),
        _RESOLVED_TTL_SECONDS,
    )


def invalidate_resolved_categories(workspace_id: str) -> None:
    """Invalida cache de qualquer template_version — chamar em write de override."""
    client = _get_redis_safe()
    if client is None:
        return
    pattern = f"categories:ws={workspace_id}:v=*"
    try:
        for key in client.scan_iter(match=pattern):
            client.delete(key)
    except Exception as exc:
        logger.warning("category cache invalidate failed for %s: %s", workspace_id, exc)


def get_cached_template(template_version: int) -> list[dict] | None:
    raw, status = _redis_get_with_status(template_cache_key(template_version))
    _record_cache_event("category_template", status)
    if raw is None:
        return None
    try:
        return list(json.loads(raw))
    except (ValueError, TypeError) as exc:
        logger.warning("template cache parse failed: %s", exc)
        return None


def store_template_cache(template_version: int, payload: list[dict]) -> None:
    _redis_set(
        template_cache_key(template_version),
        json.dumps(payload),
        _TEMPLATE_TTL_SECONDS,
    )


def invalidate_template(template_version: int) -> None:
    """Invalida cache do template — chamar quando seed Alembic publica nova versão."""
    _redis_delete(template_cache_key(template_version))


def get_latest_template_version() -> int | None:
    """Lê ``MAX(template_version)`` cacheado (chave global). ``None`` em miss/parse-fail."""
    raw, status = _redis_get_with_status(_LATEST_TEMPLATE_VERSION_KEY)
    _record_cache_event("latest_template_version", status)
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError) as exc:
        logger.warning("latest_template_version cache parse failed: %s", exc)
        return None


def set_latest_template_version(version: int) -> None:
    """Popula cache global de ``MAX(template_version)`` com TTL 15min (SRE follow-up #192)."""
    _redis_set(
        _LATEST_TEMPLATE_VERSION_KEY, str(int(version)), _LATEST_TEMPLATE_VERSION_TTL_SECONDS
    )


def invalidate_latest_template_version() -> None:
    """Apaga chave global — chamar em seed Alembic de novo ``category_template`` v(N+1)."""
    _redis_delete(_LATEST_TEMPLATE_VERSION_KEY)


# ---------------------------------------------------------------------------
# Redis primitives — falha aberta (mesmo padrão de fiscal_cache)
# ---------------------------------------------------------------------------


def _redis_get(key: str) -> str | None:
    raw, _ = _redis_get_with_status(key)
    return raw


def _redis_get_with_status(key: str) -> tuple[str | None, str]:
    """Lê chave do Redis devolvendo ``(valor, status)`` — ``status`` ∈ {hit, miss, fallback}."""
    client = _get_redis_safe()
    if client is None:
        return None, "fallback"
    try:
        raw = client.get(key)
    except Exception as exc:
        logger.warning("redis GET failed for %s: %s", key, exc)
        return None, "fallback"
    return (raw, "hit") if raw is not None else (None, "miss")


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


def _get_redis_safe() -> Any:
    try:
        from backend.app.services.pipeline.events import _get_redis

        return _get_redis()
    except Exception:
        return None
