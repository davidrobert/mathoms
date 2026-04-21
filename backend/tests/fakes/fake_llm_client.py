"""In-process LLM client fake shaped like the LiteLLM client surface.

`LLMService` calls `client.chat.completions.create(...)` once per attempt.
Tests parameterize the fake with a canned response or a raising exception.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class _Completions:
    error: Exception | None = None
    response: Any = None

    def create(self, **_kwargs: Any) -> Any:
        if self.error is not None:
            raise self.error
        return self.response


@dataclass
class _Chat:
    completions: _Completions


class FakeLLMClient:
    """Stand-in for the LiteLLM client used by `LLMService._client`."""

    def __init__(
        self,
        *,
        raises: Exception | None = None,
        response: Any = None,
    ) -> None:
        self.chat = _Chat(completions=_Completions(error=raises, response=response))
