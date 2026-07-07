"""Teste de conectividade do provider — morava em ``litellm_client.py`` até
A33.l7 estourar o teto de 500 linhas (P2, mesmo movimento do ``LLMRunSummary``
em A20.l11 e dos value objects em ADR-307); ``LLMService.test_connection``
continua sendo a interface pública (delegate)."""

from __future__ import annotations

import time
from typing import Any

from pipeline.llm.error_classification import LLM_CALL_TIMEOUT_S, classify_error


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _check_ok(config: Any, response: Any, start: float) -> dict[str, Any]:
    content = response.choices[0].message.content.strip() if response.choices else ""
    return {
        "success": True,
        "provider": config.provider,
        "model": config.model_name,
        "response": content,
        "duration_ms": _elapsed_ms(start),
    }


def _check_failed(config: Any, exc: Exception, start: float) -> dict[str, Any]:
    return {
        "success": False,
        "provider": config.provider,
        "model": config.model_name,
        "error": str(exc)[:500],
        "error_type": classify_error(exc).value,
        "duration_ms": _elapsed_ms(start),
    }


def run_connection_check(service: Any) -> dict[str, Any]:
    """Prompt mínimo contra o provider; nunca levanta — erro vira dict de resultado."""
    service._ensure_client()
    model = service._get_model_string()
    config = service._config
    start = time.monotonic()
    try:
        response = service._raw_client.completion(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
            temperature=0,
            api_key=config.api_key,
            timeout=LLM_CALL_TIMEOUT_S,
            num_retries=0,
        )
        return _check_ok(config, response, start)
    except Exception as exc:
        return _check_failed(config, exc, start)
