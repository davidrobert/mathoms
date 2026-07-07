"""Emissão de métricas no choke-point ``LLMService.call`` (A33.l7 · ADR-110).

O pipeline emite via protocol ``LLMMetricsEmitter`` injetado (padrão
``LLMCallHooks``/ADR-307); ``None`` = no-op. Falha do emitter nunca derruba
a call que já custou tokens.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from pydantic import BaseModel

from pipeline.llm.litellm_client import LLMConfig, LLMService
from tests.fakes.llm_metrics import RecordingLLMMetricsEmitter
from tests.fakes.llm_response_cache import InMemoryResponseCache


class _Out(BaseModel):
    value: str
    confidence: float = 0.9
    needs_review: bool = False


class _OutSemQuality(BaseModel):
    value: str


def _mock_response(schema=_Out, **kwargs):
    response = schema(value="ok", **kwargs)
    raw = MagicMock()
    raw.usage.prompt_tokens = 100
    raw.usage.completion_tokens = 50
    object.__setattr__(response, "_raw_response", raw)
    return response


def _build_svc(emitter, create_mock, *, response_cache=None) -> LLMService:
    svc = LLMService(
        LLMConfig(
            provider="anthropic",
            api_key="sk-test",
            model_name="claude-test",
            temperature=0.0,
            metrics_emitter=emitter,
            response_cache=response_cache,
        )
    )
    svc._ensure_client = lambda: None  # type: ignore[method-assign]
    svc._client = MagicMock()
    svc._client.chat.completions.create = create_mock
    return svc


def test_success_emits_call_quality_with_composite_labels() -> None:
    emitter = RecordingLLMMetricsEmitter()
    svc = _build_svc(emitter, MagicMock(return_value=_mock_response()))

    kwargs = dict(system_prompt="s", user_prompt="u", output_schema=_Out)
    svc.call(**kwargs, stage="extract_baseline", prompt_version="1.2.0", prompt_name="e15_baseline")

    (entry,) = emitter.call_qualities
    assert entry["prompt_name"] == "e15_baseline"
    assert entry["prompt_version"] == "1.2.0"
    assert entry["model"] == "claude-test"
    assert entry["confidence"] == 0.9 and entry["needs_review"] is False


def test_output_sem_confidence_emite_none_e_needs_review_false() -> None:
    emitter = RecordingLLMMetricsEmitter()
    svc = _build_svc(emitter, MagicMock(return_value=_mock_response(schema=_OutSemQuality)))

    svc.call(
        system_prompt="s",
        user_prompt="u",
        output_schema=_OutSemQuality,
        prompt_version="1.0.0",
        prompt_name="e1_members",
    )

    entry = emitter.call_qualities[0]
    assert entry["confidence"] is None
    assert entry["needs_review"] is False


def test_cache_miss_e_hit_emitem_cache_lookup() -> None:
    emitter = RecordingLLMMetricsEmitter()
    cache = InMemoryResponseCache()
    create_mock = MagicMock(return_value=_mock_response())
    svc = _build_svc(emitter, create_mock, response_cache=cache)

    kwargs = dict(system_prompt="s", user_prompt="u", output_schema=_Out, use_cache=True)
    kwargs.update(prompt_version="1.0.0", prompt_name="crlv", temperature=0.0)
    svc.call(**kwargs)  # miss → provider → write
    svc.call(**kwargs)  # hit → sem provider

    assert [e["hit"] for e in emitter.cache_lookups] == [False, True]
    labels = {(e["prompt_name"], e["prompt_version"]) for e in emitter.cache_lookups}
    assert labels == {("crlv", "1.0.0")}
    assert create_mock.call_count == 1
    # Hit não emite call_quality — LLMCallLog/qualidade medem custo real (ADR-307).
    assert len(emitter.call_qualities) == 1


def test_emitter_failure_does_not_break_call() -> None:
    emitter = RecordingLLMMetricsEmitter(raise_on_record=RuntimeError("collector down"))
    svc = _build_svc(emitter, MagicMock(return_value=_mock_response()))

    result = svc.call(system_prompt="s", user_prompt="u", output_schema=_Out)

    assert result.output.value == "ok"


def test_sem_emitter_mantem_comportamento_legado() -> None:
    svc = _build_svc(None, MagicMock(return_value=_mock_response()))

    result = svc.call(system_prompt="s", user_prompt="u", output_schema=_Out)

    assert result.output.value == "ok"
