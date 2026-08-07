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


# Padrões casados por substring contra `str(exc)` — NÃO contra o nome da classe.
# `_run_stage_with_retry` passa `str(exc)[:2000]` (`pipeline_task.py`), e o que
# chega ali é uma `LLMError` que re-embrulha a mensagem do provider
# (`litellm_client.py`: "LLM call failed after N attempts (Xms): <msg>").
#
# **`overloaded`/`529` e `timed out` foram acrescentados em A40.l18 por medição.**
# O overload da Anthropic — o transiente mais comum em pico de capacidade — é
# mapeado por litellm para `InternalServerError`, com mensagem que não contém
# `429`, `503`, `rate limit` nem `timeout`: não retentava, e nenhum teste
# percebia. E a mensagem de timeout aparece nas DUAS formas ("timeout" e
# "timed out"); `classify_error` já conhece ambas
# (`pipeline/llm/error_classification.py`), esta tabela conhecia só uma.
#
# O §Delta item 5 da lane A40.l18 prescrevia trocar `rate_limit` por
# `ratelimit`, alegando que o primeiro "nunca casa". A medição refuta: o corpo
# do erro traz `rate_limit_error`, que `_normalize` converte em
# `rate limit error` — `rate_limit` casa, e `ratelimit` (sem separador) NÃO.
# Aplicar a prescrição seria a regressão. Ver a nota de reconciliação na lane.
_TRANSIENT_LLM_ERRORS = [
    "timeout",
    "timed out",
    "rate_limit",
    "connection",
    "overloaded",
    "503",
    "529",
    "429",
]

# Keys descritivas (F9.2+): o orchestrator passa stage_name descritivo.
# Keys legadas aqui nunca casariam — get_retry_config normaliza via
# resolve_stage_name para aceitar ambos os formatos (W6-T03).
STAGE_RETRY_CONFIGS: dict[str, StageRetryConfig] = {
    "extract_members": StageRetryConfig(
        max_retries=2,
        retryable_errors=list(_TRANSIENT_LLM_ERRORS),
        retry_delay_seconds=10.0,
    ),
    "extract_baseline": StageRetryConfig(
        max_retries=2,
        retryable_errors=list(_TRANSIENT_LLM_ERRORS),
        retry_delay_seconds=10.0,
    ),
    "extract_with_llm": StageRetryConfig(
        max_retries=2,
        retryable_errors=list(_TRANSIENT_LLM_ERRORS),
        retry_delay_seconds=10.0,
    ),
    # NB: para este stage a tabela é inerte — `parecer_orchestrator` converte
    # toda exceção em `success: False` antes de sair, então nenhuma exceção
    # chega a `_run_stage_with_retry`. Corrigir isso é a §Follow-up item 4 da
    # A40.l18, deliberadamente NÃO feita aqui: religar o retry re-pagaria o
    # stage LLM já cobrado (regressão que a A37.l12 fechou).
    "review_finances_holistic": StageRetryConfig(
        max_retries=1,
        retryable_errors=list(_TRANSIENT_LLM_ERRORS),
        retry_delay_seconds=15.0,
    ),
}


def get_retry_config(stage_name: str) -> StageRetryConfig:
    from pipeline.stage_spec import resolve_stage_name

    return STAGE_RETRY_CONFIGS.get(resolve_stage_name(stage_name), StageRetryConfig())
