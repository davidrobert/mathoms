"""Stage retry configuration — defines which stages can be retried on failure.

Retry behavior:
- Default: 0 retries (explicit opt-in per stage)
- Only specific error types are retryable (network, timeout, transient LLM errors)
- Deterministic stages (E2, E3, etc.) don't retry by default
- LLM stages may retry on API errors
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _normalize(s: str) -> str:
    """Lowercase and collapse underscores/hyphens to spaces for fuzzy matching."""
    return s.lower().replace("_", " ").replace("-", " ")


@dataclass
class StageRetryConfig:
    max_retries: int = 0
    retryable_errors: list[str] = field(default_factory=list)
    retry_delay_seconds: float = 5.0
    backoff_factor: float = 2.0

    def should_retry(self, attempt: int, error: str) -> bool:
        if attempt >= self.max_retries:
            return False
        if not self.retryable_errors:
            return attempt < self.max_retries
        # Normalize both sides — patterns like "rate_limit" should match
        # human-formatted errors like "Rate limit exceeded".
        error_norm = _normalize(error)
        return any(_normalize(p) in error_norm for p in self.retryable_errors)

    def delay_for_attempt(self, attempt: int) -> float:
        return self.retry_delay_seconds * (self.backoff_factor**attempt)


# Keys descritivas (F9.2+): o orchestrator passa stage_name descritivo.
# Keys legadas aqui nunca casariam — get_retry_config normaliza via
# resolve_stage_name para aceitar ambos os formatos (W6-T03).
STAGE_RETRY_CONFIGS: dict[str, StageRetryConfig] = {
    "extract_members": StageRetryConfig(
        max_retries=2,
        retryable_errors=["timeout", "rate_limit", "connection", "503", "429"],
        retry_delay_seconds=10.0,
    ),
    "extract_baseline": StageRetryConfig(
        max_retries=2,
        retryable_errors=["timeout", "rate_limit", "connection", "503", "429"],
        retry_delay_seconds=10.0,
    ),
    "extract_with_llm": StageRetryConfig(
        max_retries=2,
        retryable_errors=["timeout", "rate_limit", "connection", "503", "429"],
        retry_delay_seconds=10.0,
    ),
    "review_finances_holistic": StageRetryConfig(
        max_retries=1,
        retryable_errors=["timeout", "rate_limit", "connection", "503", "429"],
        retry_delay_seconds=15.0,
    ),
}


def get_retry_config(stage_name: str) -> StageRetryConfig:
    from pipeline.stage_spec import resolve_stage_name

    return STAGE_RETRY_CONFIGS.get(resolve_stage_name(stage_name), StageRetryConfig())
