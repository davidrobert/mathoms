"""Unit — ``Event`` base class (A6e.events slice 1)."""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime

import pytest

from backend.app.events import Event

_UUID_HEX = re.compile(r"^[0-9a-f]{32}$")


def test_event_generates_hex_uuid_id():
    event = Event()
    assert _UUID_HEX.match(event.event_id), event.event_id


def test_event_timestamp_is_utc_aware():
    event = Event()
    assert event.occurred_at.tzinfo is UTC
    # clock sanity — evento acabou de ser criado
    assert (datetime.now(UTC) - event.occurred_at).total_seconds() < 1


def test_event_is_frozen():
    event = Event()
    with pytest.raises(FrozenInstanceError):
        event.workspace_id = "ws-hack"  # type: ignore[misc]


def test_event_subclass_adds_payload_fields():
    @dataclass(frozen=True, slots=True, kw_only=True)
    class _Sample(Event):
        document_id: str

    evt = _Sample(document_id="doc-1", workspace_id="ws-1")
    assert evt.document_id == "doc-1"
    assert evt.workspace_id == "ws-1"
    assert _UUID_HEX.match(evt.event_id)


def test_event_default_metadata_is_independent_per_instance():
    a = Event()
    b = Event()
    assert a.event_id != b.event_id
    assert a.occurred_at <= b.occurred_at
