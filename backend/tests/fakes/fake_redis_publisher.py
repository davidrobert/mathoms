"""In-memory fake of the Redis client used by `events.publish_event`.

Captures every `publish(channel, payload_json)` call so tests can assert
payload shape and ordering without talking to a real broker.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class PublishedMessage:
    channel: str
    raw_payload: str

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.raw_payload)


class FakeRedisPublisher:
    """Drop-in replacement for `redis.Redis` with only `publish()` implemented."""

    def __init__(self, *, publish_error: Exception | None = None) -> None:
        self.messages: list[PublishedMessage] = []
        self._publish_error = publish_error

    def publish(self, channel: str, payload: str) -> int:
        if self._publish_error is not None:
            raise self._publish_error
        self.messages.append(PublishedMessage(channel=channel, raw_payload=payload))
        return 1

    @property
    def last(self) -> PublishedMessage:
        if not self.messages:
            raise AssertionError("no message has been published yet")
        return self.messages[-1]

    def assert_published_once(self) -> PublishedMessage:
        if len(self.messages) != 1:
            raise AssertionError(f"expected exactly 1 publish, got {len(self.messages)}")
        return self.messages[0]
