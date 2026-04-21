"""Pipeline execution adapter — in-process or HTTP (A6f.1 slice 2 · ADR-112).

Two implementations behind one Protocol:

* :class:`InProcessPipelineClient` — calls ``pipeline.orchestrator._run_stage``
  in the current process. Default in dev/test, single-process deploys.
* :class:`HttpPipelineClient` — forwards to ``pipeline-service`` over HTTP.
  Engaged when ``MATHOMS_PIPELINE_SERVICE_URL`` is set.

:func:`get_pipeline_client` returns one or the other based on that env var.
Callers (currently ``backend.app.tasks.pipeline_task``) consume the Protocol
exclusively — no direct ``from pipeline.orchestrator`` imports.

Stateless (ADR-111): HTTP client holds only the base URL + a reusable
``httpx.Client``; both are idempotent singletons, safe across workers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable

import httpx


@dataclass
class StageResult:
    """Local mirror of ``pipeline.orchestrator.StageResult``.

    Duck-compatible field names (``stage``, ``success``, ``duration_ms``,
    ``detail``, ``error``) so callers don't care which client produced it.
    Defined here to keep ``backend.app.tasks.*`` free of ``pipeline.orchestrator``
    imports.
    """

    stage: str
    success: bool
    duration_ms: float = 0.0
    detail: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@runtime_checkable
class PipelineServiceClient(Protocol):
    """Backend-facing contract for running a single stage."""

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult: ...

    def is_llm_stage(self, stage: str) -> bool: ...


class InProcessPipelineClient:
    """Runs ``pipeline.orchestrator._run_stage`` in the current process."""

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult:
        from pipeline.orchestrator import _run_stage

        r = _run_stage(ctx, stage)
        return StageResult(
            stage=r.stage,
            success=r.success,
            duration_ms=r.duration_ms,
            detail=r.detail,
            error=r.error,
        )

    def is_llm_stage(self, stage: str) -> bool:
        from pipeline.stage_spec import STAGE_REGISTRY

        spec = STAGE_REGISTRY.get(stage)
        return bool(spec and spec.is_llm)


class HttpPipelineClient:
    """Forwards stage execution to pipeline-service over HTTP.

    Timeout is generous (1h): long-running stages like E3 can take minutes;
    the caller already has its own Celery soft/hard time limits.
    """

    def __init__(self, base_url: str, *, http: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = http or httpx.Client(timeout=httpx.Timeout(3600.0))

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult:
        payload = {
            "run_id": ctx.pipeline_run_id or "",
            "workspace_id": workspace_id,
            "workspace_root": str(ctx.root),
            "config_dir": str(ctx.config_dir) if ctx.config_dir else None,
            "incremental": bool(getattr(ctx, "incremental", False)),
            "incremental_doc_paths": list(
                getattr(ctx, "incremental_doc_paths", []) or []
            ),
        }
        resp = self._http.post(
            f"{self._base_url}/api/v1/pipeline/stages/{stage}/execute",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return StageResult(
            stage=data["stage"],
            success=bool(data["success"]),
            duration_ms=float(data.get("duration_ms", 0.0)),
            detail=data.get("detail"),
            error=data.get("error"),
        )

    def is_llm_stage(self, stage: str) -> bool:
        from pipeline.stage_spec import STAGE_REGISTRY

        spec = STAGE_REGISTRY.get(stage)
        return bool(spec and spec.is_llm)


_SINGLETON: PipelineServiceClient | None = None


def get_pipeline_client() -> PipelineServiceClient:
    """Return the process-wide pipeline client (idempotent singleton).

    Switches implementation based on ``MATHOMS_PIPELINE_SERVICE_URL``:
    set → :class:`HttpPipelineClient`; unset → :class:`InProcessPipelineClient`.
    """
    global _SINGLETON
    if _SINGLETON is not None:
        return _SINGLETON
    url = os.environ.get("MATHOMS_PIPELINE_SERVICE_URL", "").strip()
    if url:
        _SINGLETON = HttpPipelineClient(url)
    else:
        _SINGLETON = InProcessPipelineClient()
    return _SINGLETON


def reset_pipeline_client() -> None:
    """Test hook — force :func:`get_pipeline_client` to rebuild next call."""
    global _SINGLETON
    _SINGLETON = None
