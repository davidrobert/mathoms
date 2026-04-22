"""Unit — ``dispatch_sync`` / ``enqueue_async`` (A6e.events slice 1)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.app.events import (
    Event,
    EventHandlerDeps,
    clear_handlers,
    dispatch_sync,
    enqueue_async,
    register_handler,
)
from backend.app.events.registry import _HANDLERS


@dataclass(frozen=True, slots=True, kw_only=True)
class _OrderEvent(Event):
    payload: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class _UnregisteredEvent(Event):
    pass


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Save/restore — preserva handlers reais registrados via import."""
    snapshot = {k: list(v) for k, v in _HANDLERS.items()}
    clear_handlers()
    yield
    _HANDLERS.clear()
    _HANDLERS.update({k: list(v) for k, v in snapshot.items()})


@pytest.mark.asyncio
async def test_dispatch_sync_runs_handlers_in_registration_order():
    calls: list[str] = []

    @register_handler(_OrderEvent)
    def sync_a(event, deps):
        calls.append("a")

    @register_handler(_OrderEvent)
    async def async_b(event, deps):
        calls.append("b")

    @register_handler(_OrderEvent)
    def sync_c(event, deps):
        calls.append("c")

    await dispatch_sync(_OrderEvent(payload="x"))
    assert calls == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_dispatch_sync_unregistered_event_is_noop():
    # Não levanta, não loga, não efeito colateral
    await dispatch_sync(_UnregisteredEvent())


@pytest.mark.asyncio
async def test_dispatch_sync_propagates_handler_exception():
    @register_handler(_OrderEvent)
    def boom(event, deps):
        raise ValueError("handler falhou")

    with pytest.raises(ValueError, match="handler falhou"):
        await dispatch_sync(_OrderEvent())


@pytest.mark.asyncio
async def test_dispatch_sync_stops_at_failing_handler():
    calls: list[str] = []

    @register_handler(_OrderEvent)
    def first(event, deps):
        calls.append("first")

    @register_handler(_OrderEvent)
    def second(event, deps):
        calls.append("second")
        raise RuntimeError("abort")

    @register_handler(_OrderEvent)
    def third(event, deps):  # pragma: no cover - não deve ser chamado
        calls.append("third")

    with pytest.raises(RuntimeError, match="abort"):
        await dispatch_sync(_OrderEvent())

    assert calls == ["first", "second"]


@pytest.mark.asyncio
async def test_dispatch_sync_injects_deps_into_handler():
    captured: dict[str, object] = {}

    @register_handler(_OrderEvent)
    async def handler(event, deps):
        captured["deps"] = dict(deps)
        captured["event_payload"] = event.payload

    deps: EventHandlerDeps = {"db": object()}  # type: ignore[typeddict-item]
    await dispatch_sync(_OrderEvent(payload="hello"), deps)

    assert captured["deps"] == deps
    assert captured["event_payload"] == "hello"


@pytest.mark.asyncio
async def test_dispatch_sync_without_deps_passes_empty_mapping():
    captured: dict[str, object] = {}

    @register_handler(_OrderEvent)
    def handler(event, deps):
        captured["deps"] = dict(deps)

    await dispatch_sync(_OrderEvent())
    assert captured["deps"] == {}


def test_enqueue_async_not_yet_implemented():
    # Stub intencional — caminho async será ativado em slice dedicado.
    with pytest.raises(NotImplementedError):
        enqueue_async(_OrderEvent())
