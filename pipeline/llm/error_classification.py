"""LLM error classification — categorias retryable/non-retryable (ADR-270)."""

from __future__ import annotations

import socket
from enum import Enum


class LLMErrorType(str, Enum):
    auth = "auth"
    rate_limit = "rate_limit"
    timeout = "timeout"
    network = "network"
    validation = "validation"
    context_length = "context_length"
    provider_error = "provider_error"
    unknown = "unknown"


_NETWORK_ERROR_SUBSTRINGS = (
    "nodename",
    "servname",
    "name or service not known",
    "name resolution",
    "temporary failure in name resolution",
    "errno 8",
    "errno -2",
    "errno -3",
    "connection refused",
    "connection reset",
    "network is unreachable",
    "no route to host",
    "getaddrinfo",
    " dns ",
)


def _has_network_cause(exc: BaseException) -> bool:
    """True if any link in __cause__/__context__ chain is a stdlib network/DNS error (ADR-270)."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(
            current,
            (
                socket.gaierror,
                ConnectionRefusedError,
                ConnectionResetError,
                ConnectionAbortedError,
            ),
        ):
            return True
        current = current.__cause__ or current.__context__
    return False


_MSG_RULES: tuple[tuple[tuple[str, ...], LLMErrorType], ...] = (
    (("authentication", "api key", "unauthorized", "invalid api"), LLMErrorType.auth),
    (("rate limit", "rate_limit", "429", "too many requests"), LLMErrorType.rate_limit),
)
_MSG_RULES_POST_NETWORK: tuple[tuple[tuple[str, ...], LLMErrorType], ...] = (
    (("timeout", "timed out"), LLMErrorType.timeout),
    (("too long", "maximum context"), LLMErrorType.context_length),
    (("validation", "pydantic"), LLMErrorType.validation),
)


def classify_error(exc: Exception) -> LLMErrorType:
    """Classify an LLM exception; ``network`` precedes ``provider_error`` (SDK reembrulha DNS — ADR-270)."""
    msg = str(exc).lower()
    for needles, kind in _MSG_RULES:
        if any(n in msg for n in needles):
            return kind
    # Network detection — duas camadas (isinstance + string), ADR-270 §2.
    # Precede ``timeout`` porque mensagens DNS contêm "timed out" às vezes.
    if _has_network_cause(exc) or any(s in msg for s in _NETWORK_ERROR_SUBSTRINGS):
        return LLMErrorType.network
    if "context" in msg and "length" in msg:
        return LLMErrorType.context_length
    for needles, kind in _MSG_RULES_POST_NETWORK:
        if any(n in msg for n in needles):
            return kind
    return LLMErrorType.provider_error


def is_completion_truncated_max_tokens(exc: Exception) -> bool:
    """True when the provider cut the completion off at max_tokens (structured output then fails)."""
    msg = str(exc).lower()
    if not any(x in msg for x in ("max_tokens", "max output tokens", "maximum output")):
        return False
    return any(
        x in msg for x in ("incomplete", "length limit", "truncat", "cut off", "stopped before")
    )


# Pydantic / API caps for completion budget (aligned with backend LLMConfigCreateRequest)
MAX_COMPLETION_TOKENS_CEILING = 200_000


RETRYABLE_ERRORS = frozenset(
    {
        LLMErrorType.rate_limit,
        LLMErrorType.timeout,
        LLMErrorType.network,
        LLMErrorType.provider_error,
    }
)
BACKOFF_DELAYS = (2.0, 4.0, 8.0)
# DNS/network outage típica volta em 30-120s; backoff agressivo aguenta
# transiente sem inflar latência de erros não-network (ADR-270 §3).
BACKOFF_DELAYS_NETWORK = (30.0, 60.0, 120.0)
# Timeout BASE por-call no LiteLLM. 120s cobre p95 de prompts grandes legítimos
# (IRPF full ~50k tokens → 45-90s) sem deixar a chamada hangar em DNS failure
# (ADR-270 §1). Combinado com ``num_retries=0``, evita layering com retries
# internos do Anthropic SDK. Call-site com geração sabidamente longa (ex.:
# parecer planejador, 16k max_tokens) passa ``timeout_s`` maior em
# ``LLMService.call`` — emenda 2026-06-12 da ADR-270.
LLM_CALL_TIMEOUT_S = 120.0
# Escalada de timeout em retry (emenda ADR-270, incidente parecer 2026-06-12):
# geração que legitimamente excede o budget falha deterministicamente se o retry
# reusa o mesmo cap — 4×120s queimados sem chance de sucesso. A tentativa
# seguinte a um ``timeout`` dobra o cap (teto 600s); demais error_types mantêm
# o cap da tentativa anterior.
LLM_TIMEOUT_ESCALATION_CEILING_S = 600.0
# Teto de tentativas específico para ``timeout`` (1 base + 1 escalada). Se a
# escalada não resolveu, o problema não é budget — insistir só infla o pior
# caso (4 tentativas escalonadas ≈ 22min de stage travado).
LLM_TIMEOUT_MAX_ATTEMPTS = 2
