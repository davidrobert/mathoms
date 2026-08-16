"""HTTP stream + assemble — o Instructor não vê o generator (dogfood 2026-08-15)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipeline.llm.litellm_client import LLMConfig, LLMService
from pipeline.llm.stream_assemble import completion_via_stream


def test_completion_via_stream_forces_stream_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    chunks = [{"choices": [{"delta": {"content": "{"}}], "model": "m"}]

    def fake_completion(*_a: object, **kwargs: object) -> list:
        seen["kwargs"] = kwargs
        return chunks

    monkeypatch.setattr("litellm.completion", fake_completion)
    monkeypatch.setattr("litellm.stream_chunk_builder", lambda got, **_k: {"n": len(got)})
    out = completion_via_stream(model="anthropic/x", messages=[])
    assert out == {"n": 1}
    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["stream"] is True
    assert kwargs["stream_options"] == {"include_usage": True}


def test_completion_via_stream_does_not_mutate_caller_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = {"model": "x", "messages": []}
    monkeypatch.setattr("litellm.completion", lambda *_a, **_k: [])
    monkeypatch.setattr("litellm.stream_chunk_builder", lambda _c: {"ok": True})
    completion_via_stream(**original)
    assert "stream" not in original


def test_completion_via_stream_empty_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("litellm.completion", lambda *_a, **_k: [])
    monkeypatch.setattr("litellm.stream_chunk_builder", lambda _c: None)
    with pytest.raises(RuntimeError, match="got None"):
        completion_via_stream(model="x")


def test_ensure_client_wires_stream_assembler(monkeypatch: pytest.MonkeyPatch) -> None:
    import instructor

    captured: dict[str, object] = {}

    def fake_from_litellm(fn: object, **_kw: object) -> MagicMock:
        captured["fn"] = fn
        return MagicMock()

    monkeypatch.setattr(instructor, "from_litellm", fake_from_litellm)
    svc = LLMService(LLMConfig(provider="anthropic", api_key="sk-test", model_name="claude-test"))
    svc._ensure_client()
    assert captured["fn"] is completion_via_stream
