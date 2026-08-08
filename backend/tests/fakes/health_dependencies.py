"""Fakes das dependências que `/health` consulta — Redis, Celery e DB.

O endpoint importa cada colaborador **dentro** da função (`from backend.app.worker
import celery_app`, `from backend.app.core.database import engine`), então o patch
tem de ser no módulo, não no símbolo já ligado.
"""

from __future__ import annotations

import fakeredis
import fakeredis.aioredis


class FakeCeleryInspect:
    def active(self) -> dict:
        return {"celery@fake": []}


class FakeCeleryControl:
    def inspect(self, timeout: float | None = None) -> FakeCeleryInspect:
        return FakeCeleryInspect()


class FakeCeleryApp:
    """Worker respondendo ao ping — `checks["celery"] == "ok"`."""

    control = FakeCeleryControl()


class DeadCeleryApp:
    """Broker fora do ar — `.control.inspect` estoura e o check vira `error: ...`."""

    control = None


class FakeConnection:
    async def __aenter__(self) -> FakeConnection:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def execute(self, statement: object) -> None:
        return None


class FakeEngine:
    """`SELECT 1` responde — `checks["database"] == "ok"`."""

    def connect(self) -> FakeConnection:
        return FakeConnection()


def patch_healthy_dependencies(monkeypatch) -> None:
    """Redis, Celery e DB sadios — o cenário em que `status` deve ser "ok"."""
    import redis.asyncio as aioredis

    import backend.app.core.database as database_module
    import backend.app.worker as worker_module

    server = fakeredis.FakeServer()
    monkeypatch.setattr(
        aioredis,
        "from_url",
        lambda *a, **k: fakeredis.aioredis.FakeRedis(server=server, decode_responses=True),
    )
    monkeypatch.setattr(worker_module, "celery_app", FakeCeleryApp())
    monkeypatch.setattr(database_module, "engine", FakeEngine())
    # Se setada, o endpoint dispara probe HTTP real de 2s contra o pipeline-service.
    monkeypatch.delenv("MATHOMS_PIPELINE_SERVICE_URL", raising=False)
