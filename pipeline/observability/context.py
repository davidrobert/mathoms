"""Contextvars neutros do pipeline (ADR-273) — propagação backend→pipeline sem framework.

O backend chama :func:`bind` antes de rodar stages e :func:`reset` num
``finally`` — sem o reset, o contextvar sobrevive à task no mesmo worker
Celery e o log do run seguinte carregaria o workspace de outro tenant
(condição bloqueante do senior-cto na revisão da ADR-273). Standalone
(CLI), os getters retornam ``None`` e o logger degrada limpo.

Exceção stateless ADR-111 §1.b (request-scoped, reset garantido) —
registrada em ``docs/reference/STATELESS_AUDIT.md §2``.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

_trace_id: ContextVar[str | None] = ContextVar("pipeline_trace_id", default=None)
_workspace_id: ContextVar[str | None] = ContextVar("pipeline_workspace_id", default=None)
_run_id: ContextVar[str | None] = ContextVar("pipeline_run_id", default=None)
_stage: ContextVar[str | None] = ContextVar("pipeline_stage", default=None)


@dataclass(frozen=True)
class BindTokens:
    """Tokens de um :func:`bind` — devolva a :func:`reset` num ``finally``."""

    trace_id: Token
    workspace_id: Token
    run_id: Token
    stage: Token


def get_trace_id() -> str | None:
    return _trace_id.get()


def get_workspace_id() -> str | None:
    return _workspace_id.get()


def get_run_id() -> str | None:
    return _run_id.get()


def get_stage() -> str | None:
    return _stage.get()


def bind(
    *,
    trace_id: str | None = None,
    workspace_id: str | None = None,
    run_id: str | None = None,
    stage: str | None = None,
) -> BindTokens:
    """Seta o contexto do run e retorna tokens para :func:`reset`."""
    return BindTokens(
        trace_id=_trace_id.set(trace_id),
        workspace_id=_workspace_id.set(workspace_id),
        run_id=_run_id.set(run_id),
        stage=_stage.set(stage),
    )


def reset(tokens: BindTokens) -> None:
    """Restaura o contexto anterior — obrigatório em ``finally`` (anti-leak Celery)."""
    _trace_id.reset(tokens.trace_id)
    _workspace_id.reset(tokens.workspace_id)
    _run_id.reset(tokens.run_id)
    _stage.reset(tokens.stage)


def set_stage(stage: str | None) -> Token:
    """Seta só o stage corrente (orchestrator); devolva o token a ``reset_stage``."""
    return _stage.set(stage)


def reset_stage(token: Token) -> None:
    _stage.reset(token)
