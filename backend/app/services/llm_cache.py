"""LLM response cache (v2.9 · ADR-144)."""
# Cache de runtime para respostas LLM cacheáveis (section_summaries hoje).
# Distinto de ArtifactStore (ADR-127/128 — artefatos têm lineage e
# versionamento; cache LLM é otimização efêmera com TTL).
# Stateless rigoroso (ADR-111): backend padrão é Redis. Se Redis estiver
# indisponível, NoOpLLMCache degrada graciosamente (cache miss em toda
# chamada — generator cai no LLM ou no fallback determinístico).
# InMemoryLLMCache existe APENAS para tests; nunca em prod.

from __future__ import annotations

import logging
import time
from typing import Optional, Protocol

logger = logging.getLogger(__name__)

#: 24h em segundos (ADR-144 §2 — TTL cache section_summaries).
DEFAULT_TTL_SECONDS = 24 * 60 * 60


class LLMCacheBackend(Protocol):
    """Protocol mínimo para cache LLM."""

    def get(self, key: str) -> Optional[str]:
        """Retorna valor cacheado ou ``None`` em miss."""
        ...

    def set(self, key: str, value: str, ttl_s: int = DEFAULT_TTL_SECONDS) -> None:
        """Persiste valor com TTL em segundos."""
        ...


class NoOpLLMCache:
    """Cache que sempre dá miss — usado quando Redis indisponível."""

    # Loga warning na primeira leitura para sinalizar hit ratio = 0 em prod.

    def __init__(self) -> None:
        self._warned = False

    def get(self, key: str) -> Optional[str]:
        if not self._warned:
            logger.warning("NoOpLLMCache active — all LLM cache lookups will miss")
            self._warned = True
        return None

    def set(self, key: str, value: str, ttl_s: int = DEFAULT_TTL_SECONDS) -> None:
        return None


class RedisLLMCache:
    """Adapter Redis para o contrato ``LLMCacheBackend``."""

    # Reusa singleton _get_redis de events.py (paridade com stage_duration_estimator).
    # Falha aberta: get/set que levanta retornam miss / no-op + log.

    def __init__(self, client) -> None:
        self._client = client

    def get(self, key: str) -> Optional[str]:
        try:
            value = self._client.get(key)
        except Exception as exc:  # noqa: BLE001 — falha aberta proposital
            logger.warning("RedisLLMCache get failed for %s: %s", key, exc)
            return None
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    def set(self, key: str, value: str, ttl_s: int = DEFAULT_TTL_SECONDS) -> None:
        try:
            self._client.set(key, value, ex=int(ttl_s))
        except Exception as exc:  # noqa: BLE001 — falha aberta proposital
            logger.warning("RedisLLMCache set failed for %s: %s", key, exc)


class InMemoryLLMCache:
    """Cache em dict + TTL — APENAS para tests."""

    # Vive em backend/ (não pipeline/) para sinalizar que é adapter de
    # boundary, não service de domínio. Não usar em prod (viola ADR-111).

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ttl_s: int = DEFAULT_TTL_SECONDS) -> None:
        self._store[key] = (value, time.monotonic() + float(ttl_s))


def get_default_llm_cache() -> LLMCacheBackend:
    """Resolve o backend default — Redis se disponível, senão ``NoOpLLMCache``."""
    # Não cacheado em variável de módulo: cada chamada re-resolve.
    # _get_redis em events.py já é singleton idempotente.
    try:
        from backend.app.services.events import _get_redis

        client = _get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load Redis client for LLM cache: %s", exc)
        return NoOpLLMCache()
    if client is None:
        return NoOpLLMCache()
    return RedisLLMCache(client)


def build_section_summary_cache_key(
    workspace_id: int | str,
    snapshot_hash: str,
    section_id: str,
) -> str:
    """Compõe a chave canônica do cache para section summaries (ADR-144 §2)."""
    return f"mathoms:llm:section_summary:{workspace_id}:{snapshot_hash}:{section_id}"
