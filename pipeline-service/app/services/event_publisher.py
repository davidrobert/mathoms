"""Redis pub/sub publisher — emits events on `pipeline:{run_id}` channel.

Mirrors the envelope shape of `backend.app.services.pipeline.events` so backend and
pipeline-service are interchangeable wire-side. When Redis is unavailable
(e.g. dev without redis), publish is a no-op.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("mathoms.pipeline_service.events")

_client = None


def _get_client():
    """Lazy idempotent singleton — ADR-111 stateless-safe (same URL → same obj)."""
    global _client
    if _client is not None:
        return _client

    from app.config import load_settings

    redis_url = load_settings().redis_url
    if not redis_url:
        return None
    try:
        import redis

        _client = redis.Redis.from_url(redis_url, decode_responses=True)
        _client.ping()
    except Exception as exc:
        logger.warning("redis_unavailable url=%s err=%s", redis_url, exc)
        _client = None
    return _client


def publish(
    run_id: str,
    event_type: str,
    *,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    progress_pct: Optional[int] = None,
    error: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    """Publish an envelope to `pipeline:{run_id}`."""
    client = _get_client()
    if client is None:
        return
    payload: dict[str, Any] = {
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
    try:
        client.publish(f"pipeline:{run_id}", json.dumps(payload))
    except Exception as exc:
        logger.warning("publish_failed run=%s err=%s", run_id, exc)


def reset_client() -> None:
    """Test hook — force re-resolution next call."""
    global _client
    _client = None
