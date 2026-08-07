"""A40.l18 · ADR-357 §8 — a tabela de retry casa as mensagens que o provider produz."""

# Alimentado pelo PRODUTOR: cada `str(exc)` abaixo é a forma que `LLMError` monta
# em `pipeline/llm/litellm_client.py` ("LLM call failed after N attempts (Xms):
# <msg>") re-embrulhando a mensagem do provider. Testar contra strings inventadas
# provaria que `_normalize` funciona, não que o retry dispara.

from __future__ import annotations

import pytest

from backend.app.services.pipeline.retry_config import (
    _TRANSIENT_LLM_ERRORS,
    _normalize,
    get_retry_config,
)


def _wrapped(provider_msg: str) -> str:
    """O que `_run_stage_with_retry` recebe: `str(exc)` da LLMError re-embrulhada."""
    return f"LLM call failed after 3 attempts (48231ms): {provider_msg}"


_TRANSIENT = {
    "rate_limit_429": "Error code: 429 - {'type': 'error', 'error': {'type': 'rate_limit_error'}}",
    "overloaded_529": "Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error'}}",
    "overloaded_500": "InternalServerError: Overloaded",
    "service_unavailable_503": "Error code: 503 - service unavailable",
    "timeout_timed_out": "Request timed out.",
    "timeout_api": "APITimeoutError: Request timed out.",
    "connection_refused": "[Errno 61] Connection refused",
}

_PERMANENT = {
    "auth": "Error code: 401 - {'error': {'type': 'authentication_error'}}",
    "context_length": "Error code: 400 - prompt is too long: 250000 tokens > 200000 maximum",
    "bad_request": "Error code: 400 - {'error': {'type': 'invalid_request_error'}}",
}


@pytest.mark.parametrize("label", sorted(_TRANSIENT))
def test_transiente_retenta(label: str) -> None:
    cfg = get_retry_config("extract_with_llm")
    assert cfg.should_retry(0, _wrapped(_TRANSIENT[label])) is True


@pytest.mark.parametrize("label", sorted(_PERMANENT))
def test_permanente_nao_retenta(label: str) -> None:
    cfg = get_retry_config("extract_with_llm")
    assert cfg.should_retry(0, _wrapped(_PERMANENT[label])) is False


def test_overloaded_era_o_gap_real() -> None:
    """Regressão de A40.l18: o overload da Anthropic não retentava e ninguém via."""
    # litellm mapeia 529 / "overloaded_error" para `InternalServerError`, cuja
    # mensagem não contém `429`, `503`, `rate limit` nem `timeout` — os 5 padrões
    # que a tabela tinha antes desta lane.
    antes = ["timeout", "rate_limit", "connection", "503", "429"]
    msg = _normalize(_wrapped(_TRANSIENT["overloaded_529"]))
    assert not any(_normalize(p) in msg for p in antes)
    assert any(_normalize(p) in msg for p in _TRANSIENT_LLM_ERRORS)


def test_rate_limit_com_separador_e_o_padrao_correto() -> None:
    """A prescrição do §Delta item 5 da lane (`ratelimit`) seria a regressão."""
    # `_normalize` colapsa `_`/`-` em espaço nos DOIS lados, então o corpo do erro
    # (`rate_limit_error` → `rate limit error`) casa `rate_limit` e **não** casa
    # `ratelimit`. A premissa documentada — de que o comparando é o nome da classe
    # `RateLimitError` — nomeia o objeto errado: `should_retry` recebe `str(exc)`.
    msg = _normalize(_wrapped(_TRANSIENT["rate_limit_429"]))
    assert _normalize("rate_limit") in msg
    assert _normalize("ratelimit") not in msg


def test_timeout_precisa_das_duas_formas() -> None:
    """`classify_error` conhece "timeout" E "timed out"; a tabela conhecia uma."""
    from pipeline.llm.error_classification import _MSG_RULES_POST_NETWORK

    needles, _ = _MSG_RULES_POST_NETWORK[0]
    assert set(needles) <= set(
        _TRANSIENT_LLM_ERRORS
    ), "a tabela de retry precisa cobrir as mesmas formas de timeout que o classificador"


def test_stage_sem_config_nao_retenta() -> None:
    assert get_retry_config("analyze_finances").max_retries == 0
    assert get_retry_config("analyze_finances").should_retry(0, _wrapped("qualquer")) is False


def test_nome_legado_resolve_para_a_mesma_config() -> None:
    assert (
        get_retry_config("E6-parecer").max_retries
        == get_retry_config("review_finances_holistic").max_retries
    )
