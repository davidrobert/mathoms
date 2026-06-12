"""LLM Service — unified interface for pipeline LLM calls via LiteLLM + Instructor.

Provides:
  - Multi-provider support (Anthropic, OpenAI, Ollama, etc.) via LiteLLM
  - Structured output enforcement via Instructor + Pydantic schemas
  - Automatic retry with exponential backoff and error classification
  - Per-call token usage logging with cost estimation
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from pipeline.llm.error_classification import (
    BACKOFF_DELAYS,
    BACKOFF_DELAYS_NETWORK,
    LLM_CALL_TIMEOUT_S,
    LLM_TIMEOUT_ESCALATION_CEILING_S,
    LLM_TIMEOUT_MAX_ATTEMPTS,
    MAX_COMPLETION_TOKENS_CEILING,
    RETRYABLE_ERRORS,
    LLMErrorType,
    classify_error,
    is_completion_truncated_max_tokens,
)
from pipeline.llm.models_catalog import SUPPORTED_PROVIDERS, default_model_for
from pipeline.llm.pricing import MODEL_PRICING, estimate_cost_usd
from pipeline.llm.prompts._sanitization import sanitize_and_wrap

logger = logging.getLogger(__name__)

# Telemetria de Layer 1 (ADR-175): emite ``pattern`` (enum fechado de categoria),
# NUNCA o trecho casado — explode cardinalidade E vaza conteúdo financeiro.
_sanitization_logger = logging.getLogger("mathoms.llm.input_sanitized")

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base error for LLM calls."""

    def __init__(
        self, message: str, error_type: LLMErrorType = LLMErrorType.unknown, retryable: bool = False
    ):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


class LLMValidationError(LLMError):
    """Raised when LLM output fails schema validation after all retries."""

    def __init__(
        self, message: str, last_output: Any = None, validation_errors: list[str] | None = None
    ):
        super().__init__(message, LLMErrorType.validation, retryable=False)
        self.last_output = last_output
        self.validation_errors = validation_errors or []


@dataclass
class LLMCallResult:
    """Result of a single LLM call with usage metrics."""

    output: Any
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    total_tokens: int = 0
    cost_estimate_usd: float = 0.0
    duration_ms: int = 0
    retries_used: int = 0
    # False quando o modelo não está em ``_MODEL_PRICING``: ``cost_estimate_usd``
    # é 0.0 por convenção mas representa "desconhecido", não "grátis". Distingue
    # provedor sem custo (Ollama local) de pricing missing (modelo novo não-mapeado).
    cost_known: bool = True


@dataclass
class LLMRunSummary:
    """Aggregated token usage for an entire pipeline run."""

    calls: list[LLMCallResult] = field(default_factory=list)

    @property
    def total_tokens_in(self) -> int:
        return sum(c.tokens_in for c in self.calls)

    @property
    def total_tokens_out(self) -> int:
        return sum(c.tokens_out for c in self.calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_estimate_usd for c in self.calls)

    @property
    def total_duration_ms(self) -> int:
        return sum(c.duration_ms for c in self.calls)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": len(self.calls),
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cost_estimate_usd": round(self.total_cost_usd, 6),
            "total_duration_ms": self.total_duration_ms,
            "calls": [
                {
                    "provider": c.provider,
                    "model": c.model,
                    "tokens_in": c.tokens_in,
                    "tokens_out": c.tokens_out,
                    "cost_usd": round(c.cost_estimate_usd, 6),
                    "duration_ms": c.duration_ms,
                    "retries": c.retries_used,
                }
                for c in self.calls
            ],
        }


@dataclass
class LLMConfig:
    """Configuration for LLM calls (from DB or dict)."""

    provider: str = "anthropic"
    api_key: str = ""
    model_name: str = default_model_for("anthropic")
    max_tokens: int = 4096
    temperature: float = 0.1


# Compat: testes legados importam ``_classify_error`` deste módulo.
_classify_error = classify_error


class LLMService:
    """Orchestrates LLM calls with retry, structured output, and token tracking.

    Usage:
        config = LLMConfig(provider="anthropic", api_key="sk-...", model_name="claude-sonnet-4-6")
        service = LLMService(config)

        result = service.call(
            system_prompt="You are a financial analyst.",
            user_prompt="Extract members from this document: ...",
            output_schema=MembersExtractOutput,
        )
        print(result.output)  # MembersExtractOutput instance
        print(result.tokens_in)
    """

    def __init__(self, config: LLMConfig):
        self._config = config
        self._summary = LLMRunSummary()
        self._client = None
        self._raw_client = None

    @property
    def summary(self) -> LLMRunSummary:
        return self._summary

    def reset_summary(self) -> None:
        self._summary = LLMRunSummary()

    def _get_model_string(self) -> str:
        """Build LiteLLM model string: 'provider/model_name'."""
        provider_info = SUPPORTED_PROVIDERS.get(self._config.provider)
        if provider_info:
            return f"{provider_info['prefix']}{self._config.model_name}"
        return self._config.model_name

    def _ensure_client(self):
        """Lazy-initialize the Instructor client wrapping LiteLLM."""
        if self._client is not None:
            return

        import instructor
        import litellm

        litellm.drop_params = True

        # Silencia logs de transport do LiteLLM ("Wrapper: Completed Call...") —
        # eles não carregam contexto de stage. Nossos próprios logs (LLM call START / OK)
        # cobrem início, fim e retries com muito mais informação.
        logging.getLogger("LiteLLM").setLevel(logging.WARNING)
        logging.getLogger("litellm").setLevel(logging.WARNING)

        self._raw_client = litellm
        self._client = instructor.from_litellm(litellm.completion)

    def test_connection(self) -> dict[str, Any]:
        """Quick connectivity test — sends a minimal prompt and checks for a valid response."""
        self._ensure_client()
        model = self._get_model_string()

        start = time.monotonic()
        try:
            response = self._raw_client.completion(
                model=model,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
                max_tokens=10,
                temperature=0,
                api_key=self._config.api_key,
                timeout=LLM_CALL_TIMEOUT_S,
                num_retries=0,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            content = response.choices[0].message.content.strip() if response.choices else ""
            return {
                "success": True,
                "provider": self._config.provider,
                "model": self._config.model_name,
                "response": content,
                "duration_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            error_type = classify_error(exc)
            return {
                "success": False,
                "provider": self._config.provider,
                "model": self._config.model_name,
                "error": str(exc)[:500],
                "error_type": error_type.value,
                "duration_ms": elapsed_ms,
            }

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: Type[T],
        *,
        max_retries: int = 3,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stage: str | None = None,
        image_bytes: bytes | None = None,
        image_media_type: str = "image/jpeg",
        seed: int | None = None,
        timeout_s: float | None = None,
    ) -> LLMCallResult:
        """Call an LLM with structured output enforcement.

        Uses Instructor to auto-retry on validation failures. Additionally retries
        on transient errors (rate_limit, timeout) with exponential backoff.

        Args:
            stage: Identificador do stage chamador (ex: "E1", "E6-parecer"). Aparece
                em todos os logs desta chamada — essencial para debug quando múltiplos
                stages disputam o worker.
            image_bytes: quando fornecido, envia a imagem como content block multimodal
                junto ao user_prompt (Anthropic vision). Apenas para providers que
                suportam visão (anthropic, openai).
            image_media_type: MIME type da imagem (ex: "image/jpeg", "image/png").
            seed: best-effort determinism (eval de lineage, ADR-281). ``None`` =
                omitido do payload; provider sem suporte descarta (``drop_params``).
            timeout_s: timeout base da 1ª tentativa (default LLM_CALL_TIMEOUT_S).
                Call-site com geração longa passa valor maior — emenda ADR-270.

        Raises:
            LLMValidationError: if output fails validation after all retries
            LLMError: for non-retryable errors (auth, context_length)
        """
        import base64

        self._ensure_client()
        model = self._get_model_string()
        effective_max_tokens = max_tokens or self._config.max_tokens
        effective_temperature = temperature if temperature is not None else self._config.temperature

        # Tag de stage para todos os logs desta chamada — formato "[stage] " para scan visual rápido.
        tag = f"[{stage}] " if stage else ""

        # Layer 1 + Layer 2 (ADR-175) — choke-point único: sanitiza/sandwich
        # apenas ``user_prompt`` (dado do usuário). ``system_prompt`` é nosso,
        # controlado — nunca tocado. Call-site novo herda a defesa por construção.
        user_prompt, sanitized_patterns = sanitize_and_wrap(user_prompt)
        for pattern in sanitized_patterns:
            _sanitization_logger.warning(
                "input sanitized: pattern=%s stage=%s",
                pattern,
                stage or "unknown",
                extra={"pattern": pattern, "stage": stage or "unknown"},
            )

        prompt_chars = len(system_prompt) + len(user_prompt)
        schema_name = getattr(output_schema, "__name__", str(output_schema))

        effective_timeout = timeout_s if timeout_s is not None else LLM_CALL_TIMEOUT_S

        is_multimodal = image_bytes is not None
        logger.info(
            "%sLLM call START: model=%s max_tokens=%d temp=%.2f timeout_s=%.0f "
            "prompt_chars=%d schema=%s%s",
            tag,
            self._config.model_name,
            effective_max_tokens,
            effective_temperature,
            effective_timeout,
            prompt_chars,
            schema_name,
            f" image={len(image_bytes)}B" if is_multimodal else "",
        )

        # Monta o conteúdo do user message: texto puro ou [imagem + texto] multimodal.
        if is_multimodal:
            b64 = base64.standard_b64encode(image_bytes).decode("ascii")
            user_content: str | list = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": b64,
                    },
                },
                {"type": "text", "text": user_prompt},
            ]
        else:
            user_content = user_prompt

        seed_kwargs: dict[str, Any] = {} if seed is None else {"seed": seed}

        last_exception = None
        retries_used = 0
        timeout_attempts = 0
        start_total = time.monotonic()

        attempt = 0
        while attempt <= max_retries:
            try:
                start = time.monotonic()

                # Instructor retry mínimo: truncation é tratada pelo loop externo
                # que dobra max_tokens. Retry interno aqui só cobre erros de validação
                # pontuais (enum errado, tipo incorreto) — ver is_completion_truncated_max_tokens.
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    response_model=output_schema,
                    max_tokens=effective_max_tokens,
                    temperature=effective_temperature,
                    max_retries=1,
                    api_key=self._config.api_key,
                    # ADR-270: cap por-call + desabilita retry interno do
                    # LiteLLM/Anthropic SDK. Retries são do outer loop deste
                    # método — fonte única, observável, com backoff por tipo.
                    # Emenda 2026-06-12: cap escala após timeout (ver except).
                    timeout=effective_timeout,
                    num_retries=0,
                    **seed_kwargs,
                )

                elapsed = int((time.monotonic() - start) * 1000)

                usage = getattr(response, "_raw_response", None)
                tokens_in = 0
                tokens_out = 0
                if usage and hasattr(usage, "usage") and usage.usage:
                    tokens_in = getattr(usage.usage, "prompt_tokens", 0) or 0
                    tokens_out = getattr(usage.usage, "completion_tokens", 0) or 0

                cost = self._estimate_cost(tokens_in, tokens_out)

                result = LLMCallResult(
                    output=response,
                    provider=self._config.provider,
                    model=self._config.model_name,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    total_tokens=tokens_in + tokens_out,
                    cost_estimate_usd=cost if cost is not None else 0.0,
                    cost_known=cost is not None,
                    duration_ms=elapsed,
                    retries_used=retries_used,
                )
                self._summary.calls.append(result)

                logger.info(
                    "%sLLM call OK: model=%s tokens=%d+%d cost=$%.4f duration=%dms attempt=%d/%d",
                    tag,
                    self._config.model_name,
                    tokens_in,
                    tokens_out,
                    cost,
                    elapsed,
                    attempt + 1,
                    max_retries + 1,
                )

                return result

            except Exception as exc:
                last_exception = exc

                if is_completion_truncated_max_tokens(exc):
                    prev_cap = effective_max_tokens
                    bumped = min(effective_max_tokens * 2, MAX_COMPLETION_TOKENS_CEILING)
                    if bumped > effective_max_tokens:
                        effective_max_tokens = bumped
                        logger.warning(
                            "%sLLM completion truncated at max_tokens=%d — retrying with max_tokens=%d",
                            tag,
                            prev_cap,
                            effective_max_tokens,
                        )
                        continue

                retries_used = attempt + 1
                error_type = classify_error(exc)

                logger.warning(
                    "%sLLM call attempt %d/%d failed: type=%s timeout_s=%.0f error=%s",
                    tag,
                    attempt + 1,
                    max_retries + 1,
                    error_type.value,
                    effective_timeout,
                    str(exc)[:200],
                )

                if error_type == LLMErrorType.auth:
                    raise LLMError(
                        f"Authentication failed: {exc}", LLMErrorType.auth, retryable=False
                    ) from exc

                if error_type == LLMErrorType.context_length:
                    raise LLMError(
                        f"Context length exceeded: {exc}",
                        LLMErrorType.context_length,
                        retryable=False,
                    ) from exc

                if error_type not in RETRYABLE_ERRORS and error_type != LLMErrorType.validation:
                    if attempt >= max_retries:
                        break

                if error_type == LLMErrorType.timeout:
                    # Retry com o mesmo cap falha deterministicamente quando a geração
                    # excede o budget: dobra o cap (teto 600s) e limita a 2 tentativas —
                    # emenda ADR-270 (incidente parecer 2026-06-12).
                    timeout_attempts += 1
                    if timeout_attempts >= LLM_TIMEOUT_MAX_ATTEMPTS:
                        break
                    effective_timeout = min(effective_timeout * 2, LLM_TIMEOUT_ESCALATION_CEILING_S)

                if attempt < max_retries:
                    # ADR-270: backoff network-specific (30/60/120s) aguenta
                    # outage transiente de DNS; demais retryable usam 2/4/8s.
                    backoff_table = (
                        BACKOFF_DELAYS_NETWORK
                        if error_type == LLMErrorType.network
                        else BACKOFF_DELAYS
                    )
                    delay = backoff_table[min(attempt, len(backoff_table) - 1)]
                    if error_type == LLMErrorType.rate_limit:
                        delay *= 2
                    logger.info(
                        "%sRetrying in %.1fs (error_type=%s)...", tag, delay, error_type.value
                    )
                    time.sleep(delay)

                attempt += 1

        total_elapsed = int((time.monotonic() - start_total) * 1000)

        if last_exception and classify_error(last_exception) == LLMErrorType.validation:
            raise LLMValidationError(
                f"Output validation failed after {max_retries + 1} attempts: {last_exception}",
                last_output=None,
                validation_errors=[str(last_exception)],
            )

        raise LLMError(
            f"LLM call failed after {max_retries + 1} attempts ({total_elapsed}ms): {last_exception}",
            classify_error(last_exception) if last_exception else LLMErrorType.unknown,
            retryable=False,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> Optional[float]:
        """Custo estimado em USD; ``None`` se modelo desconhecido (ver pricing.py)."""
        return estimate_cost_usd(self._config.model_name, tokens_in, tokens_out)


# Compat: ``_MODEL_PRICING`` mantido como alias do módulo ``pricing`` para
# call-sites legados (testes). Source of truth: ``pipeline.llm.pricing``.
_MODEL_PRICING = MODEL_PRICING
