"""Prazo do run no choke-point LLM: nenhuma tentativa começa ou continua depois dele."""

# O `LLMService.call` é o único lugar por onde toda chamada LLM passa, mas não o único
# laço de retry: o instructor 1.15.1 monta `Retrying(stop=...)` sem `retry=`, e o
# default do tenacity retenta QUALQUER exceção por dentro do `create()`. A guarda que
# alcança essas tentativas mora na função que o instructor chama a cada uma delas.
# Com stream, o timeout do httpx vale por leitura e não limita uma geração em voo:
# daí a checagem por chunk, que é o que para as threads do pool (ADR-446).

from __future__ import annotations

from typing import Any, Callable

from pipeline.llm.stream_assemble import completion_via_stream
from pipeline.run_deadline import RunDeadline, RunTimeLimitExceededError, is_time_limit

# Piso do read timeout capado: zero não é "já", é comportamento indefinido no httpx.
_MIN_READ_TIMEOUT_S = 0.5


def deadline_of(hooks: object) -> RunDeadline:
    """Prazo que os hooks do run carregam; sem prazo para hooks que não o têm (CLI, testes)."""
    deadline = getattr(hooks, "run_deadline", None)
    return deadline if isinstance(deadline, RunDeadline) else RunDeadline()


def guarded_completion(deadline: RunDeadline) -> Callable[..., Any]:
    """`completion_via_stream` sob o prazo do run; sem prazo, a própria função."""
    if deadline.expires_at is None:
        return completion_via_stream

    def _completion(*args: Any, **kwargs: Any) -> Any:
        deadline.check("tentativa LLM")
        kwargs["timeout"] = _capped_timeout(kwargs.get("timeout"), deadline)
        return completion_via_stream(*args, chunk_guard=_chunk_guard(deadline), **kwargs)

    return _completion


def _chunk_guard(deadline: RunDeadline) -> Callable[[], None]:
    return lambda: deadline.check("geração LLM em curso")


def _capped_timeout(timeout: Any, deadline: RunDeadline) -> Any:
    """Read timeout que não passa do relógio do run — vale para o TTFB, antes do 1º chunk."""
    remaining = deadline.remaining_s()
    if remaining is None:
        return timeout
    cap = max(remaining, _MIN_READ_TIMEOUT_S)
    return min(timeout, cap) if isinstance(timeout, (int, float)) else cap


def raise_if_time_limit(exc: BaseException, deadline: RunDeadline) -> None:
    """No ``except`` do retry: fim de prazo dispara o prazo e relança tipado, sem classificar."""
    if not (is_time_limit(exc) or deadline.expired()):
        return
    deadline.trip()
    raise RunTimeLimitExceededError(
        f"prazo do run esgotado durante chamada LLM ({type(exc).__name__})"
    ) from exc
