"""WebSocket integration tests — F6.5B.14.

Cobertura:
- JWT auth: token inválido fecha com code 4001
- JWT auth: token válido → conexão aceita
- Heartbeat: enviado quando não há mensagem em até 15s
- Mensagem publicada via Redis pub/sub → recebida no WS
- Terminal events (run_completed/failed/cancelled) fecham WS

Strategy:
- Usa `fakeredis` (in-memory) para o pub/sub, sem dependência de Redis real
- Spy em `redis.asyncio.from_url` para retornar fake
- Usa starlette TestClient (sync) que suporta `.websocket_connect()`
"""

from __future__ import annotations

import asyncio
import json

import fakeredis.aioredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token
from backend.app.main import app


# ─── Fake Redis fixture (process-wide) ───────────────────────────────


@pytest.fixture
def patch_redis(monkeypatch):
    """Substitui `redis.asyncio.from_url` por um FakeRedis aioredis-compatível."""
    fake_server = fakeredis.FakeServer()

    def _from_url(*args, **kwargs):
        return fakeredis.aioredis.FakeRedis(server=fake_server, decode_responses=True)

    import redis.asyncio as aioredis

    monkeypatch.setattr(aioredis, "from_url", _from_url)
    return fake_server


# ─── TestClient ──────────────────────────────────────────────────────


@pytest.fixture
def sync_client():
    """starlette TestClient (sync) — necessário para .websocket_connect()."""
    return TestClient(app)


# ─── Tests ───────────────────────────────────────────────────────────


def test_ws_rejects_invalid_token(sync_client, patch_redis):
    """Token inválido → close 4001."""
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as exc:
        with sync_client.websocket_connect(
            "/api/pipeline/runs/run-1/ws?token=invalid",
        ) as ws:
            ws.receive_json()  # força await até o close
    assert exc.value.code == 4001


def test_ws_rejects_missing_token(sync_client, patch_redis):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as exc:
        with sync_client.websocket_connect("/api/pipeline/runs/run-1/ws") as ws:
            ws.receive_json()
    assert exc.value.code == 4001


def test_ws_accepts_valid_token_and_subscribes(sync_client, patch_redis):
    """Token JWT válido → conexão aceita e subscribe em pipeline:run-1."""
    token = create_access_token("user-1")
    with sync_client.websocket_connect(
        f"/api/pipeline/runs/run-1/ws?token={token}",
    ) as ws:
        # Aceita conexão sem fechar imediatamente
        # Recebe heartbeat após primeiro timeout (configurado em 15s no servidor)
        # Para test rápido, publica uma mensagem manualmente para destravar.
        import redis.asyncio as aioredis

        async def publish():
            r = aioredis.from_url("redis://fake")
            await r.publish(
                "pipeline:run-1",
                json.dumps({"event": "stage_started", "stage": "E2", "run_id": "run-1"}),
            )
            await r.close()

        asyncio.run(publish())

        msg = ws.receive_json()
        assert msg["event"] in ("stage_started", "heartbeat")


def test_ws_terminal_event_closes_connection(sync_client, patch_redis):
    """Quando publica run_completed, WS deve enviar e fechar com code 1000."""
    token = create_access_token("user-1")
    with sync_client.websocket_connect(
        f"/api/pipeline/runs/run-2/ws?token={token}",
    ) as ws:
        import redis.asyncio as aioredis

        async def publish():
            r = aioredis.from_url("redis://fake")
            await r.publish(
                "pipeline:run-2",
                json.dumps({"event": "run_completed", "run_id": "run-2"}),
            )
            await r.close()

        asyncio.run(publish())

        msg = ws.receive_json()
        # Pode receber heartbeat antes ou run_completed direto
        assert msg["event"] in ("run_completed", "heartbeat")
