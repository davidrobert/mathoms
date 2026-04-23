"""Redis Pub/Sub event publisher for pipeline progress.

Events are published to channel `pipeline:{run_id}` as JSON.
The WebSocket handler subscribes to the same channel to forward to clients.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# ADR-119: fases válidas do contrato LiveStep. Tem peso fixo no frontend
# (<LiveStepProgress/>) — adicionar valor aqui é breaking change.
LiveStepPhase = Literal["preparing", "awaiting_llm", "validating", "persisting", "finalizing"]
_LIVESTEP_PHASES = ("preparing", "awaiting_llm", "validating", "persisting", "finalizing")
_LIVESTEP_THROTTLE_MS = 250

_redis_client = None


def _get_redis():
    """Lazy-initialize Redis client (import-time safety)."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis

            from backend.app.core.config import settings

            _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as exc:
            logger.warning("Redis unavailable, events will be no-ops: %s", exc)
            _redis_client = None
    return _redis_client


def publish_event(
    run_id: str,
    event_type: str,
    *,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    progress_pct: Optional[int] = None,
    error: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    """Publish a pipeline event to Redis Pub/Sub channel."""
    client = _get_redis()
    if client is None:
        return

    payload = {
        "event": event_type,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if stage is not None:
        payload["stage"] = stage
    if status is not None:
        payload["status"] = status
    if progress_pct is not None:
        payload["progress_pct"] = progress_pct
    if error is not None:
        payload["error"] = error
    if detail is not None:
        payload["detail"] = detail

    channel = f"pipeline:{run_id}"
    try:
        client.publish(channel, json.dumps(payload))
    except Exception as exc:
        logger.warning("Failed to publish event to %s: %s", channel, exc)


def publish_stage_started(run_id: str, stage: str, progress_pct: int) -> None:
    publish_event(run_id, "stage_started", stage=stage, status="running", progress_pct=progress_pct)


def publish_stage_completed(run_id: str, stage: str, progress_pct: int) -> None:
    publish_event(
        run_id, "stage_completed", stage=stage, status="completed", progress_pct=progress_pct
    )


def publish_stage_failed(run_id: str, stage: str, error: str, progress_pct: int) -> None:
    publish_event(
        run_id, "stage_failed", stage=stage, status="failed", error=error, progress_pct=progress_pct
    )


def publish_stage_skipped(run_id: str, stage: str, reason: str, progress_pct: int) -> None:
    publish_event(
        run_id,
        "stage_skipped",
        stage=stage,
        status="skipped",
        progress_pct=progress_pct,
        detail={"reason": reason},
    )


def publish_stage_activity(
    run_id: str,
    stage: str,
    *,
    file: Optional[str] = None,
    message: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Fine-grained progress within a stage (current file, sub-step message)."""
    detail: dict[str, Any] = {}
    if message:
        detail["message"] = message
    if file:
        detail["file"] = file
    if extra:
        detail.update(extra)
    publish_event(
        run_id,
        "stage_activity",
        stage=stage,
        status="running",
        detail=detail if detail else None,
    )


def _livestep_throttle_allows(run_id: str, stage: str) -> bool:
    # Rate limit via Redis SET NX PX (ADR-111: nunca throttle em memória).
    # Falha aberta: sem Redis ou exceção → permite emissão.
    client = _get_redis()
    if client is None:
        return True
    try:
        acquired = client.set(
            f"livestep:th:{run_id}:{stage}", "1", nx=True, px=_LIVESTEP_THROTTLE_MS
        )
    except Exception as exc:
        logger.warning("livestep throttle check failed, allowing emit: %s", exc)
        return True
    return bool(acquired)


def publish_item_progress(
    run_id: str,
    stage: str,
    *,
    current_item: Optional[str],
    items_done: int,
    items_total: int,
    phase: LiveStepPhase,
    estimated_duration_ms: Optional[int] = None,
) -> None:
    """Emit LiveStep per-item progress (ADR-119).

    Throttled to 1 event / 250ms per (run_id, stage). `phase="finalizing"`
    sempre emite (usuário precisa ver a conclusão do último item).
    """
    if phase not in _LIVESTEP_PHASES:
        raise ValueError(f"invalid LiveStep phase: {phase!r} (expected one of {_LIVESTEP_PHASES})")
    if not (0 <= items_done <= items_total):
        raise ValueError(f"items_done={items_done} out of [0, items_total={items_total}]")
    if phase != "finalizing" and not _livestep_throttle_allows(run_id, stage):
        return
    detail: dict[str, Any] = {
        "items_done": items_done,
        "items_total": items_total,
        "phase": phase,
    }
    if current_item is not None:
        detail["current_item"] = current_item
    if estimated_duration_ms is not None:
        detail["estimated_duration_ms"] = estimated_duration_ms
    publish_event(run_id, "stage_activity", stage=stage, status="running", detail=detail)


def publish_needs_review(run_id: str, stage: str) -> None:
    publish_event(run_id, "needs_review", stage=stage, status="needs_review")


def publish_run_completed(run_id: str) -> None:
    publish_event(run_id, "run_completed", status="completed", progress_pct=100)


def publish_run_failed(run_id: str) -> None:
    publish_event(run_id, "run_failed", status="failed")


def publish_run_cancelled(run_id: str) -> None:
    publish_event(run_id, "run_cancelled", status="cancelled")


def reset_redis_client() -> None:
    """For testing — force re-initialization."""
    global _redis_client
    _redis_client = None
