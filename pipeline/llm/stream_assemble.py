"""HTTP stream + assemble: o Instructor vê 1 ModelResponse, não o generator."""

from __future__ import annotations

import contextlib
from typing import Any, Callable


def completion_via_stream(
    *args: Any, chunk_guard: Callable[[], None] | None = None, **kwargs: Any
) -> Any:
    """litellm.completion(stream=True) + stream_chunk_builder (EOF TTFB ~120s)."""
    import litellm

    kwargs = dict(kwargs)
    kwargs["stream"] = True
    kwargs.setdefault("stream_options", {"include_usage": True})
    stream = litellm.completion(*args, **kwargs)
    chunks = list(stream) if chunk_guard is None else _drain_guarded(stream, chunk_guard)
    assembled = litellm.stream_chunk_builder(chunks)
    if assembled is None:
        raise RuntimeError(f"expected ModelResponse from stream, got None (chunks={len(chunks)})")
    return assembled


def _drain_guarded(stream: Any, chunk_guard: Callable[[], None]) -> list[Any]:
    """Consome o stream chamando a guarda a cada chunk; se ela levanta, fecha o stream."""
    chunks: list[Any] = []
    try:
        for chunk in stream:
            chunk_guard()
            chunks.append(chunk)
    except BaseException:
        _close_quietly(stream)
        raise
    return chunks


def _close_quietly(stream: Any) -> None:
    """Libera a conexão já — o wrapper sync do litellm só expõe ``aclose``."""
    for target in (stream, getattr(stream, "completion_stream", None)):
        close = getattr(target, "close", None)
        if callable(close):
            with contextlib.suppress(Exception):
                close()
            return
