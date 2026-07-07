"""In-process LLM client fake shaped like the LiteLLM client surface.

`LLMService` calls `client.chat.completions.create(...)` once per attempt.
Tests parameterize the fake with a canned response or a raising exception.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class FakeSequenceLLMClient:
    """Stand-in para ``LLMService.call`` com 1 output programado por chamada.

    Entradas podem ser Pydantic model (vira ``LLMCallResult.output``) ou
    ``Exception`` (levantada) — cobre o drift-check nightly (A33.l5), que
    faz 1 trial por fixture em sequência. CI nunca chama Anthropic.
    """

    outputs: list[Any] = field(default_factory=list)
    provider: str = "fake"
    model: str = "fake-llm"
    calls: int = 0
    seen_kwargs: list[dict[str, Any]] = field(default_factory=list)

    def call(self, **kwargs: Any) -> Any:
        from pipeline.llm.litellm_client import LLMCallResult

        self.seen_kwargs.append(kwargs)
        entry = self.outputs[self.calls]
        self.calls += 1
        if isinstance(entry, Exception):
            raise entry
        return LLMCallResult(
            output=entry,
            provider=self.provider,
            model=self.model,
            tokens_in=1000,
            tokens_out=400,
            total_tokens=1400,
            cost_estimate_usd=0.009,
            duration_ms=1200,
            retries_used=0,
        )
