"""Stage duration estimator — mediana cacheada de ``duration_ms`` por stage.

ADR-119 (item 5). Cache em Redis com TTL de 5min (estateless — ADR-111).
Falha aberta: se Redis indisponível, vai direto ao DB; se DB falha,
retorna dict vazio. Consumidores (Celery task em ``pipeline_task._setup_run_context``)
populam ``ctx.stage_duration_estimates`` com o retorno.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from backend.app.repositories.pipeline_stage_log_repository import (
    PipelineStageLogRepository,
)

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300


def _cache_key(workspace_id: str) -> str:
    return f"livestep:estimates:{workspace_id}"


def get_cached_stage_estimates(session: Session, workspace_id: str) -> dict[str, int]:
    """Retorna ``{stage: median_duration_ms}``, cacheado 5min por workspace."""
    cached = _load_from_cache(workspace_id)
    if cached is not None:
        return cached
    estimates = _query_estimates(session, workspace_id)
    _store_in_cache(workspace_id, estimates)
    return estimates


def invalidate_stage_estimates(workspace_id: str) -> None:
    """Invalida o cache para o workspace (ex.: após run completar)."""
    client = _get_redis_safe()
    if client is None:
        return
    try:
        client.delete(_cache_key(workspace_id))
    except Exception as exc:
        logger.warning("Failed to invalidate stage estimates cache: %s", exc)


def _query_estimates(session: Session, workspace_id: str) -> dict[str, int]:
    try:
        return PipelineStageLogRepository(session).get_median_durations_for_workspace(workspace_id)
    except Exception as exc:
        logger.warning("Failed to query stage medians, using empty: %s", exc)
        return {}


def _load_from_cache(workspace_id: str) -> dict[str, int] | None:
    client = _get_redis_safe()
    if client is None:
        return None
    try:
        raw = client.get(_cache_key(workspace_id))
    except Exception as exc:
        logger.warning("Cache read failed for stage estimates: %s", exc)
        return None
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
        return {str(k): int(v) for k, v in parsed.items()}
    except (ValueError, TypeError) as exc:
        logger.warning("Cache parse failed for stage estimates: %s", exc)
        return None


def _store_in_cache(workspace_id: str, estimates: dict[str, int]) -> None:
    client = _get_redis_safe()
    if client is None:
        return
    try:
        client.set(_cache_key(workspace_id), json.dumps(estimates), ex=_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Cache write failed for stage estimates: %s", exc)


def _get_redis_safe():
    try:
        from backend.app.services.events import _get_redis

        return _get_redis()
    except Exception:
        return None
