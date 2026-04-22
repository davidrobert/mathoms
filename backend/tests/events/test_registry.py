"""Unit — ``register_handler`` / ``handlers_for`` (A6e.events slice 1)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.app.events import Event, clear_handlers, register_handler
from backend.app.events.registry import handlers_for


@dataclass(frozen=True, slots=True, kw_only=True)
class _EventA(Event):
    payload: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class _EventB(Event):
    payload: str = ""


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_handlers()
    yield
    clear_handlers()


def test_register_handler_stores_callable_under_event_class():
    @register_handler(_EventA)
    def handler(event, deps):
        return None

    assert handlers_for(_EventA) == [handler]
    assert handlers_for(_EventB) == []


def test_handlers_for_unknown_class_is_empty():
    assert handlers_for(_EventA) == []


def test_registration_order_is_preserved():
    @register_handler(_EventA)
    def first(event, deps):
        return None

    @register_handler(_EventA)
    def second(event, deps):
        return None

    @register_handler(_EventA)
    def third(event, deps):
        return None

    assert handlers_for(_EventA) == [first, second, third]


def test_handlers_for_returns_copy_not_shared_reference():
    @register_handler(_EventA)
    def handler(event, deps):
        return None

    first_view = handlers_for(_EventA)
    first_view.clear()  # mutação na cópia
    assert handlers_for(_EventA) == [handler]


def test_registration_across_event_types_is_isolated():
    @register_handler(_EventA)
    def for_a(event, deps):
        return None

    @register_handler(_EventB)
    def for_b(event, deps):
        return None

    assert handlers_for(_EventA) == [for_a]
    assert handlers_for(_EventB) == [for_b]


def test_clear_handlers_removes_all_registrations():
    @register_handler(_EventA)
    def handler(event, deps):
        return None

    clear_handlers()
    assert handlers_for(_EventA) == []
