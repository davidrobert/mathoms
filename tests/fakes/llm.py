"""Fakes nomeados para tests de LLM (v2.9 · ADR-144)."""
# CLAUDE.md §Testes "Mocks de I/O externo via fakes nomeados, não MagicMock".
# Cobre cenários do generator: success, timeout, rate_limit, invalid JSON,
# provider 5xx — sem bater Anthropic API em CI.

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from pipeline.domain.services.section_summary_generator import LLMRawResponse
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
