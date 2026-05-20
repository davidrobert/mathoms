"""Stream de progresso de pipeline via Redis Pub/Sub → WebSocket."""

from __future__ import annotations

import asyncio
import json
import logging

import jwt
from fastapi import WebSocket, WebSocketDisconnect
from jwt.exceptions import InvalidTokenError

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_TERMINAL_EVENTS = {"run_completed", "run_failed", "run_cancelled"}


def verify_ws_token(token: str) -> str | None:
    """Valida JWT do handshake WebSocket. Retorna ``user_id`` ou ``None``."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        return user_id
    except InvalidTokenError:
        return None


async def stream_pipeline_progress(websocket: WebSocket, run_id: str) -> None:
    """Assina ``pipeline:{run_id}`` e encaminha eventos para o socket.

    Fecha o socket em evento terminal (run_completed/failed/cancelled) ou
    degrada com mensagem de erro se Redis indisponível. Heartbeats a cada
    15s sem evento mantêm conexão viva.
    """
    subscription = await _subscribe(websocket, run_id)
    if subscription is None:
        return
    redis_client, redis_sub = subscription
    try:
        await _pump_messages(websocket, redis_sub)
    except WebSocketDisconnect:
        logger.debug("WS client disconnected for run %s", run_id)
    except Exception as exc:
        logger.warning("WS error for run %s: %s", run_id, exc)
    finally:
        await _cleanup(redis_client, redis_sub, run_id)


async def _subscribe(websocket: WebSocket, run_id: str):
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.cache_redis_url, decode_responses=True)
        redis_sub = redis_client.pubsub()
        await redis_sub.subscribe(f"pipeline:{run_id}")
        return redis_client, redis_sub
    except Exception as exc:
        logger.warning("Redis unavailable for WS subscription: %s", exc)
        await websocket.send_json(
            {"event": "error", "detail": "Real-time updates unavailable. Use polling."}
        )
        await websocket.close(code=1011, reason="Redis unavailable")
        return None


async def _pump_messages(websocket: WebSocket, redis_sub) -> None:
    while True:
        try:
            message = await asyncio.wait_for(
                redis_sub.get_message(ignore_subscribe_messages=True, timeout=15.0),
                timeout=20.0,
            )
        except asyncio.TimeoutError:
            await websocket.send_json({"event": "heartbeat"})
            continue

        if not (message and message["type"] == "message"):
            await websocket.send_json({"event": "heartbeat"})
            continue

        if await _forward(websocket, message):
            return


async def _forward(websocket: WebSocket, message: dict) -> bool:
    """Envia mensagem ao cliente. Retorna True se evento é terminal."""
    try:
        data = json.loads(message["data"])
    except json.JSONDecodeError as exc:
        logger.warning("Error decoding WS message: %s", exc)
        return False
    await websocket.send_json(data)
    if data.get("event") in _TERMINAL_EVENTS:
        await websocket.close(code=1000, reason="Run finished")
        return True
    return False


async def _cleanup(redis_client, redis_sub, run_id: str) -> None:
    try:
        await redis_sub.unsubscribe(f"pipeline:{run_id}")
        await redis_sub.close()
        await redis_client.close()
    except Exception:
        pass
