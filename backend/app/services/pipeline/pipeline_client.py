"""Pipeline execution adapter — in-process or HTTP (A6f.1 slice 2 · ADR-112).

Three implementations behind one Protocol:

* :class:`InProcessPipelineClient` — calls ``pipeline.orchestrator._run_stage``
  in the current process. Default in dev/test, single-process deploys.
* :class:`HttpPipelineClient` — forwards to ``pipeline-service`` over HTTP.
  Engaged when ``MATHOMS_PIPELINE_SERVICE_URL`` is set.
* :class:`FallbackPipelineClient` — decorates the HTTP client with a
  run-scoped circuit breaker (ADR-323): on a shell-level failure
  (``ConnectError``/connect-timeout/5xx) it degrades to InProcess for the
  rest of the run instead of hard-failing every stage. Opt-in via
  ``MATHOMS_PIPELINE_SHELL_FALLBACK`` (default off — see ADR-323 §Default).

:func:`get_pipeline_client` composes them based on those two env vars.
Callers (currently ``backend.app.tasks.pipeline_task``) consume the Protocol
exclusively — no direct ``from pipeline.orchestrator`` imports.

Stateless (ADR-111): every client holds only immutable refs (base URL,
reusable ``httpx.Client``, wrapped clients). The circuit-breaker state is
run-scoped, living on ``ctx.shell_degraded`` — never on the singleton.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

#: Connect/pool timeout — a dead or unreachable shell must degrade fast, not
#: hang for the full stage budget. Read/write stay generous (below) because
#: LLM stages legitimately take minutes.
_CONNECT_TIMEOUT_S = 5.0
#: Read/write timeout — long-running stages (E3/E5) can take minutes; the
#: caller has its own Celery soft/hard time limits as the outer bound.
_STAGE_IO_TIMEOUT_S = 3600.0

#: Env var gating the auto-fallback (ADR-323). Default off: during the soak
#: window a shell-caused stage failure MUST surface (rollback trigger #2),
#: so masking it via silent degrade is wrong until post-F3.
_SHELL_FALLBACK_ENV = "MATHOMS_PIPELINE_SHELL_FALLBACK"

#: Transport failures that guarantee the shell never committed → safe to
#: degrade. Connection never established (``ConnectError``) or timed out
#: before the request was sent (``ConnectTimeout``/``PoolTimeout``). A
#: ``ReadTimeout`` is deliberately excluded: the stage may still be running
#: on the shell and could commit later, so re-running InProcess risks a
#: concurrent double-write (ADR-323 §Escopo do gatilho).
_DEGRADE_ON_CONNECT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)

#: Marker injected into ``StageResult.detail`` when a stage was served by the
#: fallback executor. Lands in ``pipeline_stage_logs.output_summary`` (DB,
#: queryable for the soak ledger); does not touch ``pipeline_artifacts`` so
#: ``go_parity_gate`` is unaffected.
_FALLBACK_DETAIL_KEY = "_shell_fallback"


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
        from pipeline.stage_spec import STAGE_REGISTRY, resolve_stage_name

        spec = STAGE_REGISTRY.get(resolve_stage_name(stage))
        return bool(spec and spec.is_llm)


class HttpPipelineClient:
    """Forwards stage execution to pipeline-service over HTTP.

    Timeout is split (ADR-323): connect/pool are short (``_CONNECT_TIMEOUT_S``)
    so an unreachable shell degrades fast, while read/write stay generous
    (1h) because long-running stages like E3/E5 take minutes. A single flat
    3600s timeout would make ``ConnectTimeout``/``PoolTimeout`` hang for an
    hour before the fallback could trip — worse than the plain hard-fail.
    """

    def __init__(self, base_url: str, *, http: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = http or httpx.Client(
            timeout=httpx.Timeout(
                connect=_CONNECT_TIMEOUT_S,
                read=_STAGE_IO_TIMEOUT_S,
                write=_STAGE_IO_TIMEOUT_S,
                pool=_CONNECT_TIMEOUT_S,
            )
        )

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult:
        payload = {
            "run_id": ctx.pipeline_run_id or "",
            "workspace_id": workspace_id,
            "workspace_root": str(ctx.root),
            "config_dir": str(ctx.config_dir) if ctx.config_dir else None,
            "incremental": bool(getattr(ctx, "incremental", False)),
            "incremental_doc_paths": list(getattr(ctx, "incremental_doc_paths", []) or []),
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
        from pipeline.stage_spec import STAGE_REGISTRY, resolve_stage_name

        spec = STAGE_REGISTRY.get(resolve_stage_name(stage))
        return bool(spec and spec.is_llm)


def _annotate_fallback(result: StageResult, trigger: Optional[str] = None) -> StageResult:
    """Copy ``detail`` (never mutate the InProcess dict) and add the ``_shell_fallback`` marker so the DB stage log records the executor."""
    detail = dict(result.detail) if isinstance(result.detail, dict) else {}
    detail[_FALLBACK_DETAIL_KEY] = {"executor": "inprocess", "trigger": trigger}
    return StageResult(
        stage=result.stage,
        success=result.success,
        duration_ms=result.duration_ms,
        detail=detail,
        error=result.error,
    )


def _log_shell_fallback(*, stage: str, workspace_id: str, run_id: str, trigger: str) -> None:
    """LOUD structured signal on the circuit trip (ADR-323) — feeds rollback trigger #2 + soak ledger."""
    from pipeline.observability.logger import get_logger

    extra = {
        "event": "pipeline_shell_fallback",
        "stage": stage,
        "workspace_id": workspace_id,
        "pipeline_run_id": run_id,
        "trigger_class": trigger,
    }
    get_logger("shell_fallback").error(
        "pipeline_shell_fallback stage=%s trigger=%s — Go shell unavailable, "
        "degrading to InProcess for the rest of the run",
        stage,
        trigger,
        extra=extra,
    )


class FallbackPipelineClient:
    """Run-scoped circuit breaker over the HTTP client (ADR-323): on a shell-level failure it degrades to ``fallback`` (InProcess) and trips ``ctx.shell_degraded`` so later stages of the same run skip the downed shell (composition owns the resilience policy; ``primary`` owns HTTP transport). Trigger scope + idempotency rationale in ADR-323 and the ``_DEGRADE_ON_CONNECT`` constant."""

    def __init__(
        self,
        primary: PipelineServiceClient,
        fallback: PipelineServiceClient,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult:
        if getattr(ctx, "shell_degraded", False):
            return _annotate_fallback(
                self._fallback.execute_stage(ctx, stage, workspace_id=workspace_id),
                trigger=None,
            )
        try:
            return self._primary.execute_stage(ctx, stage, workspace_id=workspace_id)
        except _DEGRADE_ON_CONNECT as exc:
            return self._degrade(ctx, stage, workspace_id=workspace_id, trigger=type(exc).__name__)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status < 500:
                raise  # 4xx = contract bug (unknown stage / bad payload); hard-fail
            return self._degrade(ctx, stage, workspace_id=workspace_id, trigger=f"http_{status}")

    def _degrade(self, ctx, stage: str, *, workspace_id: str, trigger: str) -> StageResult:
        ctx.shell_degraded = True
        _log_shell_fallback(
            stage=stage,
            workspace_id=workspace_id,
            run_id=getattr(ctx, "pipeline_run_id", "") or "",
            trigger=trigger,
        )
        return _annotate_fallback(
            self._fallback.execute_stage(ctx, stage, workspace_id=workspace_id),
            trigger=trigger,
        )

    def is_llm_stage(self, stage: str) -> bool:
        return self._primary.is_llm_stage(stage)


_SINGLETON: PipelineServiceClient | None = None


def _shell_fallback_enabled() -> bool:
    return os.environ.get(_SHELL_FALLBACK_ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def get_pipeline_client() -> PipelineServiceClient:
    """Return the process-wide pipeline client (idempotent singleton).

    * ``MATHOMS_PIPELINE_SERVICE_URL`` unset → :class:`InProcessPipelineClient`.
    * set, ``MATHOMS_PIPELINE_SHELL_FALLBACK`` off → :class:`HttpPipelineClient`
      (legacy hard-fail on shell down/5xx).
    * set, fallback on → :class:`HttpPipelineClient` wrapped in
      :class:`FallbackPipelineClient` (auto-degrade to InProcess — ADR-323).
    """
    global _SINGLETON
    if _SINGLETON is not None:
        return _SINGLETON
    url = os.environ.get("MATHOMS_PIPELINE_SERVICE_URL", "").strip()
    if not url:
        _SINGLETON = InProcessPipelineClient()
    elif _shell_fallback_enabled():
        _SINGLETON = FallbackPipelineClient(HttpPipelineClient(url), InProcessPipelineClient())
    else:
        _SINGLETON = HttpPipelineClient(url)
    return _SINGLETON


def reset_pipeline_client() -> None:
    """Test hook — force :func:`get_pipeline_client` to rebuild next call."""
    global _SINGLETON
    _SINGLETON = None
