"""Fakes nomeados para tests de LLM (v2.9 · ADR-144)."""
# CLAUDE.md §Testes "Mocks de I/O externo via fakes nomeados, não MagicMock".
# Cobre cenários do generator: success, timeout, rate_limit, invalid JSON,
# provider 5xx — sem bater Anthropic API em CI.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic import BaseModel

from pipeline.domain.services.section_summary_generator import LLMRawResponse
from pipeline.llm.litellm_client import LLMCallResult
from pipeline.llm.schemas.section_summaries import SectionSummaryOutput


@dataclass
class FakeLLMSuccess:
    """LLM client que sempre retorna o mesmo output programado."""

    text: str = "Summary determinístico do fake."
    tone: str = "neutral"
    key_metric_ref: Optional[str] = None
    prompt_tokens: int = 1500
    completion_tokens: int = 300
    calls: int = 0

    def call(self, *, system_prompt: str, user_prompt: str, section_id: str) -> LLMRawResponse:
        self.calls += 1
        return LLMRawResponse(
            output=SectionSummaryOutput(
                summary_md=self.text,
                tone=self.tone,  # type: ignore[arg-type]
                key_metric_ref=self.key_metric_ref,
            ),
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )


@dataclass
class FakeLLMRaisingClient:
    """LLM client que sempre levanta — usado para forçar fallback."""

    error: Exception
    calls: int = 0

    def call(self, *, system_prompt: str, user_prompt: str, section_id: str) -> LLMRawResponse:
        self.calls += 1
        raise self.error


def make_fake_fallback(text: str = "fallback determinístico") -> Callable:
    """Fallback simples para tests — retorna sempre o mesmo texto."""

    def _fallback(section_id, snapshot_data):
        return text

    return _fallback


@dataclass
class FakeStructuredLLMClient:
    """Stand-in para `LLMService.call` — output Pydantic pré-programado, sem API."""

    output: BaseModel
    tokens_in: int = 1500
    tokens_out: int = 800
    duration_ms: int = 2500
    provider: str = "fake"
    model: str = "fake-llm"
    calls: int = 0
    last_kwargs: dict[str, Any] = field(default_factory=dict)

    def call(self, **kwargs) -> LLMCallResult:
        self.calls += 1
        self.last_kwargs = kwargs
        return LLMCallResult(
            output=self.output,
            provider=self.provider,
            model=self.model,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            total_tokens=self.tokens_in + self.tokens_out,
            cost_estimate_usd=0.0165,
            duration_ms=self.duration_ms,
            retries_used=0,
        )
