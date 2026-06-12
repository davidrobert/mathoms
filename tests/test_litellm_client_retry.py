"""Guardrails de ADR-270 — classificação network, backoff dedicado, timeout cap, no internal retries."""

from __future__ import annotations

import socket
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from pipeline.llm.error_classification import (
    BACKOFF_DELAYS,
    BACKOFF_DELAYS_NETWORK,
    LLM_CALL_TIMEOUT_S,
    LLM_TIMEOUT_ESCALATION_CEILING_S,
    LLM_TIMEOUT_MAX_ATTEMPTS,
    RETRYABLE_ERRORS,
    LLMErrorType,
    classify_error,
)
from pipeline.llm.litellm_client import LLMConfig, LLMError, LLMService


class _Out(BaseModel):
    value: str


def _build_svc_with_mock_client(create_mock: MagicMock) -> LLMService:
    """Helper: LLMService com Instructor client mockado para create().__chat__.completions."""
    svc = LLMService(LLMConfig(provider="anthropic", api_key="sk-test", model_name="claude-test"))
    svc._ensure_client = lambda: None  # type: ignore[method-assign]
    svc._client = MagicMock()
    svc._client.chat.completions.create = create_mock
    return svc


# ---------- classificação ----------


def test_classify_error_gaierror_strict() -> None:
    """gaierror via __cause__ chain → network."""
    inner = socket.gaierror(8, "nodename nor servname provided, or not known")
    outer = RuntimeError("wrapped failure")
    outer.__cause__ = inner
    assert classify_error(outer) == LLMErrorType.network


def test_classify_error_gaierror_via_context() -> None:
    """gaierror exposta apenas via __context__ (raise dentro de except) também é detectada."""
    inner = socket.gaierror(8, "name resolution failed")
    outer = RuntimeError("re-raised")
    outer.__context__ = inner
    assert classify_error(outer) == LLMErrorType.network


def test_classify_error_litellm_internal_with_errno8_string() -> None:
    """Caso real do incidente: litellm reembrulha sem preservar __cause__ — string fallback."""
    exc = Exception(
        "litellm.InternalServerError: AnthropicException - "
        "[Errno 8] nodename nor servname provided, or not known. "
        "Handle with `litellm.InternalServerError`."
    )
    assert classify_error(exc) == LLMErrorType.network


def test_classify_error_connection_refused() -> None:
    exc = ConnectionRefusedError("connection refused")
    assert classify_error(exc) == LLMErrorType.network


def test_classify_error_getaddrinfo_string() -> None:
    exc = Exception("getaddrinfo failed for api.anthropic.com")
    assert classify_error(exc) == LLMErrorType.network


def test_classify_error_auth_still_wins() -> None:
    """auth e rate_limit têm precedência sobre network (ordem na função)."""
    exc = Exception("Invalid API key")
    assert classify_error(exc) == LLMErrorType.auth


def test_classify_error_provider_error_when_no_network_signal() -> None:
    """Generic provider error sem signal de rede continua provider_error."""
    exc = Exception("internal server error from anthropic")
    assert classify_error(exc) == LLMErrorType.provider_error


def test_network_is_retryable() -> None:
    assert LLMErrorType.network in RETRYABLE_ERRORS


# ---------- backoff ----------


def test_network_backoff_is_longer_than_default() -> None:
    """DNS outage típica volta em 30-120s; usar mesma tabela 2/4/8s desperdiça retries."""
    assert BACKOFF_DELAYS_NETWORK == (30.0, 60.0, 120.0)
    assert BACKOFF_DELAYS == (2.0, 4.0, 8.0)
    # Sanity: cada entrada network é maior que a correspondente default
    for net, default in zip(BACKOFF_DELAYS_NETWORK, BACKOFF_DELAYS):
        assert net > default


# ---------- timeout cap ----------


def test_timeout_cap_constant() -> None:
    """Cap de 120s cobre p95 legítimo sem permitir hang DNS de 600s+ (ADR-270)."""
    assert LLM_CALL_TIMEOUT_S == 120.0


def test_call_propagates_timeout_and_disables_internal_retries() -> None:
    """ADR-270: retry loop é fonte única; SDK não pode layering retries internos transparentes."""
    fake_response = MagicMock()
    fake_response._raw_response = None
    create_mock = MagicMock(return_value=fake_response)
    svc = _build_svc_with_mock_client(create_mock)
    svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out)
    kwargs = create_mock.call_args.kwargs
    assert kwargs["timeout"] == LLM_CALL_TIMEOUT_S
    assert kwargs["num_retries"] == 0


# ---------- escalada de timeout (emenda ADR-270, incidente parecer 2026-06-12) ----------

_TIMEOUT_EXC = Exception(
    "litellm.Timeout: AnthropicException - litellm.Timeout: "
    "Connection timed out after 120.0 seconds."
)


def test_timeout_escalates_on_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry após timeout dobra o cap — reusar 120s contra geração >120s falha sempre."""
    monkeypatch.setattr("pipeline.llm.litellm_client.time.sleep", lambda s: None)
    create_mock = MagicMock(side_effect=_TIMEOUT_EXC)
    svc = _build_svc_with_mock_client(create_mock)
    with pytest.raises(LLMError) as excinfo:
        svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out)
    assert excinfo.value.error_type == LLMErrorType.timeout
    timeouts = [c.kwargs["timeout"] for c in create_mock.call_args_list]
    assert timeouts == [LLM_CALL_TIMEOUT_S, LLM_CALL_TIMEOUT_S * 2]


def test_timeout_attempts_capped_below_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout para após LLM_TIMEOUT_MAX_ATTEMPTS mesmo com max_retries maior — se a
    escalada não resolveu, o problema não é budget; insistir infla o pior caso."""
    monkeypatch.setattr("pipeline.llm.litellm_client.time.sleep", lambda s: None)
    create_mock = MagicMock(side_effect=_TIMEOUT_EXC)
    svc = _build_svc_with_mock_client(create_mock)
    with pytest.raises(LLMError):
        svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out, max_retries=3)
    assert create_mock.call_count == LLM_TIMEOUT_MAX_ATTEMPTS


def test_timeout_escalation_respects_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Base custom alta (timeout_s=400) escala para o teto de 600s, não 800s."""
    monkeypatch.setattr("pipeline.llm.litellm_client.time.sleep", lambda s: None)
    create_mock = MagicMock(side_effect=_TIMEOUT_EXC)
    svc = _build_svc_with_mock_client(create_mock)
    with pytest.raises(LLMError):
        svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out, timeout_s=400.0)
    timeouts = [c.kwargs["timeout"] for c in create_mock.call_args_list]
    assert timeouts == [400.0, LLM_TIMEOUT_ESCALATION_CEILING_S]


def test_custom_timeout_s_propagated_on_success() -> None:
    """Call-site com geração longa (parecer) passa timeout_s base maior que o default."""
    fake_response = MagicMock()
    fake_response._raw_response = None
    create_mock = MagicMock(return_value=fake_response)
    svc = _build_svc_with_mock_client(create_mock)
    svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out, timeout_s=240.0)
    assert create_mock.call_args.kwargs["timeout"] == 240.0


def test_non_timeout_errors_do_not_escalate(monkeypatch: pytest.MonkeyPatch) -> None:
    """provider_error mantém o cap base em todas as tentativas (escalada é só p/ timeout)."""
    monkeypatch.setattr("pipeline.llm.litellm_client.time.sleep", lambda s: None)
    create_mock = MagicMock(side_effect=Exception("internal server error from anthropic"))
    svc = _build_svc_with_mock_client(create_mock)
    with pytest.raises(LLMError):
        svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out, max_retries=2)
    timeouts = {c.kwargs["timeout"] for c in create_mock.call_args_list}
    assert timeouts == {LLM_CALL_TIMEOUT_S}
    assert create_mock.call_count == 3


# ---------- backoff selection (smoke) ----------


def test_network_error_uses_network_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha de rede dispara sleep com tabela network (30/60/120s) — não com 2s default."""
    sleeps: list[float] = []
    monkeypatch.setattr("pipeline.llm.litellm_client.time.sleep", lambda s: sleeps.append(s))
    dns_exc = Exception("AnthropicException - [Errno 8] nodename nor servname provided")
    svc = _build_svc_with_mock_client(MagicMock(side_effect=dns_exc))
    with pytest.raises(LLMError) as excinfo:
        svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out, max_retries=2)
    assert excinfo.value.error_type == LLMErrorType.network
    # 3 attempts → 2 sleeps entre elas, vindas da tabela network.
    assert sleeps == [BACKOFF_DELAYS_NETWORK[0], BACKOFF_DELAYS_NETWORK[1]]
