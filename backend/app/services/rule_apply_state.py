"""Redis-backed estado do apply retroativo async — TTL 24h idempotency + 7d status (ADR-188 PR3)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("rule_apply_state")

_IDEMPOTENCY_TTL_S: int = 24 * 60 * 60
_STATUS_TTL_S: int = 7 * 24 * 60 * 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_redis():
    """Lazy singleton Redis — paridade com ``backend.app.services.pipeline.events``."""
    # Reuso intencional: mesma URL, mesma policy; evita conexão extra.
    from backend.app.services.pipeline.events import _get_redis as _events_redis

    return _events_redis()


def _idem_key(workspace_id: str, rule_id: str) -> str:
    return f"apply_retroactive:{workspace_id}:{rule_id}"


def _status_key(workspace_id: str, rule_id: str) -> str:
    return f"apply_status:{workspace_id}:{rule_id}"


def mark_pending(*, workspace_id: str, rule_id: str, job_id: str) -> None:
    """Marca job como pendente — chamado pelo router antes do ``delay()``."""
    client = _get_redis()
    if client is None:
        logger.warning("rule_apply_state.redis_unavailable mark_pending=%s", rule_id)
        return
    client.setex(_idem_key(workspace_id, rule_id), _IDEMPOTENCY_TTL_S, "pending")
    client.hset(
        _status_key(workspace_id, rule_id),
        mapping={
            "status": "pending",
            "job_id": job_id,
            "started_at": _now_iso(),
            "applied_count": "0",
            "failed_count": "0",
        },
    )
    client.expire(_status_key(workspace_id, rule_id), _STATUS_TTL_S)


def mark_completed(*, workspace_id: str, rule_id: str, applied_count: int) -> None:
    """Marca job como concluído — chamado pelo Celery worker no finally happy-path."""
    client = _get_redis()
    if client is None:
        return
    client.setex(_idem_key(workspace_id, rule_id), _IDEMPOTENCY_TTL_S, "completed")
    client.hset(
        _status_key(workspace_id, rule_id),
        mapping={
            "status": "completed",
            "completed_at": _now_iso(),
            "applied_count": str(applied_count),
        },
    )
    client.expire(_status_key(workspace_id, rule_id), _STATUS_TTL_S)


def mark_failed(*, workspace_id: str, rule_id: str, error: str) -> None:
    """Marca job como falho — chamado pelo Celery worker no except."""
    client = _get_redis()
    if client is None:
        return
    client.setex(_idem_key(workspace_id, rule_id), _IDEMPOTENCY_TTL_S, "failed")
    client.hset(
        _status_key(workspace_id, rule_id),
        mapping={
            "status": "failed",
            "completed_at": _now_iso(),
            "error": error[:2000],
        },
    )
    client.expire(_status_key(workspace_id, rule_id), _STATUS_TTL_S)


def get_status(*, workspace_id: str, rule_id: str) -> Optional[dict[str, Any]]:
    """Retorna dict de status — ``None`` se job nunca foi disparado."""
    client = _get_redis()
    if client is None:
        return None
    raw = client.hgetall(_status_key(workspace_id, rule_id))
    if not raw:
        return None
    return _normalize_status_payload(raw)


def _normalize_status_payload(raw: dict) -> dict[str, Any]:
    """Converte hash Redis em DTO — ``applied_count`` como int."""
    payload: dict[str, Any] = dict(raw)
    for int_field in ("applied_count", "failed_count"):
        if int_field in payload:
            try:
                payload[int_field] = int(payload[int_field])
            except (TypeError, ValueError):
                payload[int_field] = 0
    return payload


def is_already_completed(*, workspace_id: str, rule_id: str) -> bool:
    """``True`` se idempotency key indica que job já foi finalizado com sucesso
    (Celery retry — não reprocessar)."""
    client = _get_redis()
    if client is None:
        return False
    return client.get(_idem_key(workspace_id, rule_id)) == "completed"
