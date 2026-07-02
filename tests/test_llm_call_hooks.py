"""Hooks de FinOps no choke-point ``LLMService.call`` (ADR-173).

Budget check pré-call (hard-stop propaga, sem gastar tokens) + record_call
pós-sucesso (falha de telemetria nunca derruba a call).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from pipeline.llm.call_hooks import LLMBudgetExceededError
from pipeline.llm.litellm_client import LLMConfig, LLMService


class _Out(BaseModel):
    value: str


class _RecordingHooks:
    """Fake nomeado (convenção tests/fakes) — captura invocações."""

    def __init__(self, budget_error: Exception | None = None, record_error: Exception | None = None):
        self.budget_error = budget_error
        self.record_error = record_error
        self.check_calls = 0
        self.recorded: list[dict] = []

    def check_budget(self) -> None:
        self.check_calls += 1
        if self.budget_error is not None:
            raise self.budget_error

    def record_call(self, result, *, stage, prompt_version) -> None:
        if self.record_error is not None:
            raise self.record_error
        self.recorded.append(
            {"result": result, "stage": stage, "prompt_version": prompt_version}
        )


def _mock_response(value: str = "ok"):
    response = _Out(value=value)
    raw = MagicMock()
    raw.usage.prompt_tokens = 100
    raw.usage.completion_tokens = 50
    object.__setattr__(response, "_raw_response", raw)
    return response


def _build_svc(hooks, create_mock: MagicMock) -> LLMService:
    svc = LLMService(
        LLMConfig(
            provider="anthropic",
            api_key="sk-test",
            model_name="claude-test",
            call_hooks=hooks,
        )
    )
    svc._ensure_client = lambda: None  # type: ignore[method-assign]
    svc._client = MagicMock()
    svc._client.chat.completions.create = create_mock
    return svc


def test_budget_exceeded_blocks_before_provider_call() -> None:
    hooks = _RecordingHooks(
        budget_error=LLMBudgetExceededError("ws-1", spent_usd=6, budget_usd=5)
    )
    create_mock = MagicMock()
    svc = _build_svc(hooks, create_mock)

    with pytest.raises(LLMBudgetExceededError):
        svc.call(system_prompt="s", user_prompt="u", output_schema=_Out)

    assert hooks.check_calls == 1
    create_mock.assert_not_called()


def test_success_records_call_with_stage_and_prompt_version() -> None:
    hooks = _RecordingHooks()
    create_mock = MagicMock(return_value=_mock_response())
    svc = _build_svc(hooks, create_mock)

    result = svc.call(
        system_prompt="s",
        user_prompt="u",
        output_schema=_Out,
        stage="E1",
        prompt_version="e1:v3",
    )

    assert result.tokens_in == 100 and result.tokens_out == 50
    assert len(hooks.recorded) == 1
    entry = hooks.recorded[0]
    assert entry["stage"] == "E1"
    assert entry["prompt_version"] == "e1:v3"
    assert entry["result"] is result


def test_record_call_failure_does_not_break_call() -> None:
    hooks = _RecordingHooks(record_error=RuntimeError("db down"))
    create_mock = MagicMock(return_value=_mock_response())
    svc = _build_svc(hooks, create_mock)

    result = svc.call(system_prompt="s", user_prompt="u", output_schema=_Out)

    assert result.output.value == "ok"


def test_no_hooks_keeps_legacy_behavior() -> None:
    create_mock = MagicMock(return_value=_mock_response())
    svc = LLMService(
        LLMConfig(provider="anthropic", api_key="sk-test", model_name="claude-test")
    )
    svc._ensure_client = lambda: None  # type: ignore[method-assign]
    svc._client = MagicMock()
    svc._client.chat.completions.create = create_mock

    result = svc.call(system_prompt="s", user_prompt="u", output_schema=_Out)

    assert result.output.value == "ok"
