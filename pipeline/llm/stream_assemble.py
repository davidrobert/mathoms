"""HTTP stream + assemble: o Instructor vê 1 ModelResponse, não o generator."""

from __future__ import annotations

from typing import Any


def completion_via_stream(*args: Any, **kwargs: Any) -> Any:
    """litellm.completion(stream=True) + stream_chunk_builder (EOF TTFB ~120s)."""
    import litellm

    kwargs = dict(kwargs)
    kwargs["stream"] = True
    kwargs.setdefault("stream_options", {"include_usage": True})
    chunks = list(litellm.completion(*args, **kwargs))
    assembled = litellm.stream_chunk_builder(chunks)
    if assembled is None:
        raise RuntimeError(f"expected ModelResponse from stream, got None (chunks={len(chunks)})")
    return assembled
