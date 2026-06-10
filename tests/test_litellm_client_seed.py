"""Seed opcional em LLMService.call (ADR-281) — kwarg chega ao client; default não muda payload."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from pipeline.llm.litellm_client import LLMConfig, LLMService


class _Out(BaseModel):
    value: str


def _build_svc_with_mock_client(create_mock: MagicMock) -> LLMService:
    svc = LLMService(LLMConfig(provider="anthropic", api_key="sk-test", model_name="claude-test"))
    svc._ensure_client = lambda: None  # type: ignore[method-assign]
    svc._client = MagicMock()
    svc._client.chat.completions.create = create_mock
    return svc


def _fake_response() -> MagicMock:
    response = MagicMock()
    response._raw_response = None
    return response


def test_seed_kwarg_reaches_client() -> None:
    create_mock = MagicMock(return_value=_fake_response())
    svc = _build_svc_with_mock_client(create_mock)
    svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out, seed=42)
    assert create_mock.call_args.kwargs["seed"] == 42


def test_seed_default_omitted_from_payload() -> None:
    """seed=None não pode virar ``seed: null`` no payload — chamadas existentes ficam intactas."""
    create_mock = MagicMock(return_value=_fake_response())
    svc = _build_svc_with_mock_client(create_mock)
    svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out)
    assert "seed" not in create_mock.call_args.kwargs


def test_seed_persists_across_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry do outer loop reenvia o mesmo seed — determinismo não degrada após falha transiente."""
    monkeypatch.setattr("pipeline.llm.litellm_client.time.sleep", lambda s: None)
    create_mock = MagicMock(side_effect=[Exception("rate limit exceeded"), _fake_response()])
    svc = _build_svc_with_mock_client(create_mock)
    svc.call(system_prompt="sys", user_prompt="usr", output_schema=_Out, seed=7, max_retries=1)
    assert len(create_mock.call_args_list) == 2
    assert all(c.kwargs["seed"] == 7 for c in create_mock.call_args_list)
