"""Fake nomeado do ``LLMResponseCache`` (ADR-307) — dict em memória, sem TTL."""

from __future__ import annotations

from pipeline.llm.response_cache import LLM_RESPONSE_CACHE_TTL_S


class InMemoryResponseCache:
    """Satisfaz o Protocol ``LLMResponseCache``; registra keys/TTLs para asserts."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.set_calls: list[tuple[str, int]] = []
        self.get_calls: list[str] = []

    def get(self, key: str) -> str | None:
        self.get_calls.append(key)
        return self.store.get(key)

    def set(self, key: str, value: str, ttl_s: int = LLM_RESPONSE_CACHE_TTL_S) -> None:
        self.set_calls.append((key, ttl_s))
        self.store[key] = value
