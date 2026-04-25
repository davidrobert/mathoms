"""
Pipeline Orchestrator — sequencia stages usando wrappers com WorkspaceContext.

Fornece execução programática do pipeline (ou subconjuntos dele),
substituindo a necessidade de invocar scripts via subprocess.

Uso:
    from pipeline.orchestrator import run_pipeline, run_from
    from pipeline.context import WorkspaceContext

    ctx = WorkspaceContext.default()
    result = run_pipeline(ctx)                     # Pipeline determinístico completo
    result = run_from(ctx, "E3")                   # De E3 em diante
    result = run_stages(ctx, ["E5", "E5.N"])       # Stages específicos
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


@dataclass
class StageResult:
    stage: str
    success: bool
    duration_ms: float = 0.0
    detail: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class PipelineResult:
    stages: List[StageResult] = field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    @property
    def success(self) -> bool:
        return all(s.success for s in self.stages)

    @property
    def failed_stage(self) -> Optional[str]:
        for s in self.stages:
            if not s.success:
                return s.stage
        return None

    def summary(self) -> dict:
        return {
            "success": self.success,
            "total_stages": len(self.stages),
            "passed": sum(1 for s in self.stages if s.success),
            "failed": sum(1 for s in self.stages if not s.success),
            "failed_stage": self.failed_stage,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


from pipeline.stage_spec import (
    DETERMINISTIC_ORDER,
    FULL_ORDER,
    LEGACY_FROM_ALIASES,
    STAGE_REGISTRY,
    build_from_map,
)

# OTel API é framework-neutral (ADR-110) e seguro importar em pipeline/.
# Sem provider configurado, chamadas são no-op (zero overhead em CLI/tests).
try:
    from opentelemetry import trace as _otel_trace

    _TRACER = _otel_trace.get_tracer("mathoms.pipeline.orchestrator")
except ImportError:  # pragma: no cover — OTel é dep do backend, não do pipeline CLI isolado.
    _TRACER = None


LLM_STAGES = {name for name, spec in STAGE_REGISTRY.items() if spec.is_llm}


def _build_from_map_with_aliases() -> Dict[str, List[str]]:
    """``FROM_MAP`` derivado de ``FULL_ORDER`` + aliases legados.

    Os aliases (``"E0"``, ``"E2"``, ``"E7"``) mapeiam para o primeiro stage do
    grupo (``"E0-unlock"``, ``"E2-faturas"``, ``"E7-crossval"``). Aceitos por
    retrocompatibilidade com call-sites que passam o prefixo da família.
    """
    base = build_from_map(FULL_ORDER)
    for alias, target in LEGACY_FROM_ALIASES.items():
        base[alias] = base[target][:]
    # E1 alias: inclui E1 em diante
    if "E1" in base:
        pass  # já presente
    return base


FROM_MAP: Dict[str, List[str]] = _build_from_map_with_aliases()


def _get_stage_runner(stage: str) -> Callable:
    """Lazy-import do runner correto para cada stage."""
    if stage == "E0-unlock":
        from pipeline.stages.unlock_documents import run

        return run
    if stage == "E0-audit":
        from pipeline.stages.audit_documents import run

        return run
    if stage == "E0-route":
        from pipeline.stages.route_documents import run

        return run
    if stage == "E1":
        from pipeline.stages.extract_members import run

        return run
    if stage == "E1.5":
        from pipeline.stages.extract_baseline import run

        return run
    if stage == "E1.5c":
        from pipeline.stages.consolidate_baseline import run

        return run
    if stage == "E2-llm":
        from pipeline.stages.extract_with_llm import run

        return run
    if stage == "E2-faturas":
        from pipeline.stages.extract_invoices import run

        return run
    if stage == "E2-extratos":
        from pipeline.stages.extract_statements import run

        return run
    if stage == "E3":
        from pipeline.stages.reconcile_transactions import run

        return run
    if stage == "E4":
        from pipeline.stages.categorize_transactions import run

        return run
    if stage == "E5":
        from pipeline.stages.analyze_finances import run

        return run
    if stage == "E5.N":
        from pipeline.stages.generate_narratives import run

        return run
    if stage == "E7-crossval":
        from pipeline.stages.e7 import run_crossval

        return run_crossval
    if stage == "E7-review":
        from pipeline.stages.review_finances import run

        return run
    if stage == "E7-apply":
        from pipeline.stages.e7 import run_apply

        return run_apply
    return None


def _run_stage(ctx: WorkspaceContext, stage: str) -> StageResult:
    """Executa um stage individual e retorna StageResult.

    Captures stdout/stderr so that error messages from legacy scripts (which
    print to stderr before calling sys.exit(1)) are included in the result.

    Catches SystemExit from legacy scripts that call sys.exit() on error.
    In CLI mode sys.exit() terminates the process (expected). In Celery worker
    mode it would kill the fork pool worker (catastrophic). Converting to
    StageResult(success=False) lets the task handle it gracefully.

    **Convenção — retorno ``dict`` e chave ``success``**

    Runners que retornam um ``dict`` (ex.: E2-llm, E5.N) podem sinalizar falha
    **sem** lançar exceção, incluindo ``"success": false`` no dicionário.

    - Se o retorno **não** é ``dict``, ou é ``dict`` **sem** a chave
      ``"success"``, o stage é considerado **bem-sucedido** (desde que não haja
      exceção).
    - Se o retorno é ``dict`` **com** ``"success"``, ``StageResult.success``
      segue ``bool(detail["success"])``. O ``detail`` completo é preservado em
      ``StageResult.detail`` (erros parciais, métricas, etc.).

    Documentação: ``docs/ARCHITECTURE.md`` (seção *Padrões arquiteturais*).
    """
    import io
    import sys
    import time
    from contextlib import nullcontext

    runner = _get_stage_runner(stage)
    if runner is None:
        return StageResult(stage=stage, success=False, error=f"No runner found for {stage}")

    # OTel span por stage (ADR-110). No-op quando provider não configurado —
    # zero overhead em CLI e testes de pipeline sem backend.
    if _TRACER is not None:
        span_cm = _TRACER.start_as_current_span(
            f"pipeline.{stage}",
            attributes={
                "pipeline.stage": stage,
                "pipeline.workspace_root": str(ctx.root),
                "pipeline.run_id": ctx.pipeline_run_id or "",
                "pipeline.is_llm": STAGE_REGISTRY[stage].is_llm
                if stage in STAGE_REGISTRY
                else False,
            },
        )
    else:
        span_cm = nullcontext()

    # Capture stderr to extract error messages from legacy scripts
    original_stderr = sys.stderr
    original_stdout = sys.stdout
    captured_stderr = io.StringIO()
    captured_stdout = io.StringIO()
    sys.stderr = captured_stderr
    sys.stdout = captured_stdout

    start = time.monotonic()
    try:
        with span_cm as span:
            try:
                detail = runner(ctx)
                elapsed = (time.monotonic() - start) * 1000
                # Wrappers que retornam dict podem sinalizar falha parcial/total sem exceção
                # (ex.: E2-llm com erros em alguns arquivos, E5.N sem output).
                ok = True
                if isinstance(detail, dict) and "success" in detail:
                    ok = bool(detail.get("success"))
                if span is not None and not ok:
                    span.set_attribute("pipeline.success", False)
                return StageResult(stage=stage, success=ok, duration_ms=elapsed, detail=detail)
            except SystemExit as exc:
                elapsed = (time.monotonic() - start) * 1000
                code = exc.code if exc.code is not None else 0
                if code == 0:
                    return StageResult(
                        stage=stage, success=True, duration_ms=elapsed, detail={"exit_code": 0}
                    )
                if span is not None:
                    span.set_attribute("pipeline.success", False)
                    span.set_attribute("pipeline.exit_code", code)
                error_msg = _extract_error_message(
                    captured_stderr.getvalue(), captured_stdout.getvalue(), code
                )
                return StageResult(stage=stage, success=False, duration_ms=elapsed, error=error_msg)
            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                if span is not None:
                    span.record_exception(exc)
                    span.set_attribute("pipeline.success", False)
                return StageResult(stage=stage, success=False, duration_ms=elapsed, error=str(exc))
    finally:
        sys.stderr = original_stderr
        sys.stdout = original_stdout


def _extract_error_message(stderr: str, stdout: str, exit_code: int) -> str:
    """Build a user-friendly error message from captured script output."""
    # Look for [ERROR], FATAL, or last non-empty lines in stderr then stdout
    for output in (stderr, stdout):
        for line in reversed(output.strip().splitlines()):
            line = line.strip()
            if not line:
                continue
            # Prefer lines with error markers
            for marker in ("[ERROR]", "FATAL", "Error:", "ERROR:"):
                if marker in line:
                    return line
    # Fallback: last non-empty line from either stream
    for output in (stderr, stdout):
        lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
        if lines:
            return lines[-1]
    return f"Script exited with code {exit_code}"


def run_stages(
    ctx: WorkspaceContext,
    stages: List[str],
    *,
    skip_llm: bool = True,
    stop_on_error: bool = True,
) -> PipelineResult:
    """Executa uma lista arbitrária de stages em ordem."""
    result = PipelineResult(started_at=datetime.now().isoformat())

    for stage in stages:
        if skip_llm and stage in LLM_STAGES:
            result.stages.append(
                StageResult(
                    stage=stage,
                    success=True,
                    detail={"skipped": True, "reason": "LLM stage skipped"},
                )
            )
            continue

        sr = _run_stage(ctx, stage)
        result.stages.append(sr)
        print(f"  [{stage}] {'OK' if sr.success else 'FAIL'} ({sr.duration_ms:.0f}ms)")

        if not sr.success and stop_on_error:
            break

    result.finished_at = datetime.now().isoformat()
    return result


def run_pipeline(
    ctx: WorkspaceContext,
    *,
    skip_llm: bool = True,
    stop_on_error: bool = True,
) -> PipelineResult:
    """Executa pipeline determinístico completo (pula LLM stages)."""
    stages = DETERMINISTIC_ORDER if skip_llm else FULL_ORDER
    return run_stages(ctx, stages, skip_llm=skip_llm, stop_on_error=stop_on_error)


def run_from(
    ctx: WorkspaceContext,
    from_stage: str,
    *,
    skip_llm: bool = True,
    stop_on_error: bool = True,
) -> PipelineResult:
    """Executa pipeline a partir de um stage específico."""
    stages = FROM_MAP.get(from_stage)
    if stages is None:
        result = PipelineResult(started_at=datetime.now().isoformat())
        result.stages.append(
            StageResult(
                stage=from_stage,
                success=False,
                error=f"Invalid from_stage: {from_stage}. Valid: {list(FROM_MAP.keys())}",
            )
        )
        result.finished_at = datetime.now().isoformat()
        return result

    return run_stages(ctx, stages, skip_llm=skip_llm, stop_on_error=stop_on_error)
