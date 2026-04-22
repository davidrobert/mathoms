"""Redis Pub/Sub event publisher for pipeline progress.

Events are published to channel `pipeline:{run_id}` as JSON.
The WebSocket handler subscribes to the same channel to forward to clients.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

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
