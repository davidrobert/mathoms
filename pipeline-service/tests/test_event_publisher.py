"""Event publisher tests using fakeredis (no real Redis required)."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def fake_redis(monkeypatch):
    """Inject a fakeredis Redis into the publisher singleton."""
    fakeredis = pytest.importorskip("fakeredis")

    client = fakeredis.FakeRedis(decode_responses=True)
    from app.services import event_publisher

    monkeypatch.setattr(event_publisher, "_client", client)
    return client


def test_publish_emits_envelope_on_channel(fake_redis):
    pubsub = fake_redis.pubsub()
    pubsub.subscribe("pipeline:run-1")
    pubsub.get_message(timeout=1)  # eat subscribe confirmation

    from app.services.event_publisher import publish

    publish("run-1", "stage_started", stage="E3", status="running", progress_pct=30)

    msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
    assert msg is not None
    payload = json.loads(msg["data"])
    assert payload["event"] == "stage_started"
    assert payload["run_id"] == "run-1"
    assert payload["stage"] == "E3"
    assert payload["progress_pct"] == 30


def test_publish_noop_when_redis_unavailable(monkeypatch):
    """With _client=None and no env → publish is silent, never raises."""
    from app.services import event_publisher

    monkeypatch.setattr(event_publisher, "_client", None)
    monkeypatch.delenv("REDIS_URL", raising=False)

    # Must not raise
    event_publisher.publish("run-1", "stage_started", stage="E3")
