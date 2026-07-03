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
    resolve_stage_name,
)

# OTel API é framework-neutral (ADR-110) e seguro importar em pipeline/.
# Sem provider configurado, chamadas são no-op (zero overhead em CLI/tests).
try:
    from opentelemetry import trace as _otel_trace

    _TRACER = _otel_trace.get_tracer("mathoms.pipeline.orchestrator")
except ImportError:  # pragma: no cover — OTel é dep do backend, não do pipeline CLI isolado.
    _TRACER = None


_LLM_DESCRIPTIVE = {name for name, spec in STAGE_REGISTRY.items() if spec.is_llm}
# Inclui aliases legados para que call-sites com ``"E1"``/``"E2-llm"`` etc.
# continuem sendo detectados como LLM stages durante a janela de compat.
from pipeline.stage_spec import DESCRIPTIVE_TO_LEGACY as _D2L  # noqa: E402

LLM_STAGES = _LLM_DESCRIPTIVE | {_D2L[d] for d in _LLM_DESCRIPTIVE if d in _D2L}


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


def _build_from_map_descriptive_with_legacy() -> Dict[str, List[str]]:
    """Estende ``FROM_MAP`` com keys legadas mapeando para sequência descritiva.

    Permite ``run_from("E3")`` continuar funcionando enquanto consumers migram.
    """
    base = _build_from_map_with_aliases()
    from pipeline.stage_spec import LEGACY_TO_DESCRIPTIVE

    for legacy, descriptive in LEGACY_TO_DESCRIPTIVE.items():
        if descriptive in base and legacy not in base:
            base[legacy] = base[descriptive][:]
    return base


FROM_MAP: Dict[str, List[str]] = _build_from_map_descriptive_with_legacy()


# Registry declarativo: stage descritivo → (módulo, atributo).
# Manter sincronizado com STAGE_REGISTRY — a guard `_assert_runners_cover_registry`
# falha import se divergir, eliminando a classe de bug "stage no registry mas
# sem runner" que recorreu em b0024c7 (extract_irpf_full).
_STAGE_RUNNERS: Dict[str, tuple[str, str]] = {
    "unlock_documents": ("pipeline.stages.unlock_documents", "run"),
    "route_documents": ("pipeline.stages.route_documents", "run"),
    "extract_members": ("pipeline.stages.extract_members", "run"),
    "extract_baseline": ("pipeline.stages.extract_baseline", "run"),
    "consolidate_baseline": ("pipeline.stages.consolidate_baseline", "run"),
    "extract_irpf_full": ("pipeline.stages.extract_irpf_full", "run"),
    "extract_informe_aluguel": ("pipeline.stages.extract_informe_aluguel", "run"),
    "extract_informes_anuais": ("pipeline.stages.extract_informes_anuais", "run"),
    "extract_comprovantes_bens": ("pipeline.stages.extract_comprovantes_bens", "run"),
    "extract_invoices": ("pipeline.stages.extract_invoices", "run"),
    "extract_statements": ("pipeline.stages.extract_statements", "run"),
    "extract_with_llm": ("pipeline.stages.extract_with_llm", "run"),
    "reconcile_transactions": ("pipeline.stages.reconcile_transactions", "run"),
    "categorize_transactions": ("pipeline.stages.categorize_transactions", "run"),
    "analyze_finances": ("pipeline.stages.analyze_finances", "run"),
    "generate_narratives": ("pipeline.stages.generate_narratives", "run"),
    "validate_cross": ("pipeline.stages.validate_cross", "run"),
    "review_finances_holistic": ("pipeline.stages.parecer_planejador", "run"),
}


def _assert_runners_cover_registry() -> None:
    """Falha import se ``STAGE_REGISTRY`` e ``_STAGE_RUNNERS`` divergirem."""
    registry_keys = set(STAGE_REGISTRY)
    runner_keys = set(_STAGE_RUNNERS)
    missing = registry_keys - runner_keys
    extra = runner_keys - registry_keys
    if missing or extra:
        raise RuntimeError(
            "Pipeline stage registries divergiram (sync STAGE_REGISTRY ↔ _STAGE_RUNNERS). "
            f"Stages sem runner: {sorted(missing)}. Runners sem stage: {sorted(extra)}."
        )


_assert_runners_cover_registry()


def _get_stage_runner(stage: str) -> Optional[Callable]:
    """Lazy-import do runner correto para cada stage.

    Aceita nomes legados (``"E3"``) ou descritivos (``"reconcile_transactions"``)
    via ``resolve_stage_name``.
    """
    import importlib

    stage = resolve_stage_name(stage)
    spec = _STAGE_RUNNERS.get(stage)
    if spec is None:
        return None
    module_path, attr = spec
    return getattr(importlib.import_module(module_path), attr)


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

    Documentação: ``docs/reference/ARCHITECTURE.md`` (seção *Padrões arquiteturais*).
    """
    import io
    import logging
    import sys
    import time
    from contextlib import nullcontext

    from pipeline.observability import StageLogTail, get_logger
    from pipeline.observability.context import reset_stage, set_stage

    runner = _get_stage_runner(stage)
    if runner is None:
        return StageResult(stage=stage, success=False, error=f"No runner found for {stage}")

    obs_logger = get_logger("orchestrator")
    stage_token = set_stage(resolve_stage_name(stage))
    tail = StageLogTail()
    logging.getLogger("mathoms.pipeline").addHandler(tail)

    # OTel span por stage (ADR-110). No-op quando provider não configurado —
    # zero overhead em CLI e testes de pipeline sem backend.
    if _TRACER is not None:
        span_cm = _TRACER.start_as_current_span(
            f"pipeline.{stage}",
            attributes={
                "pipeline.stage": stage,
                "pipeline.workspace_root": str(ctx.root),
                "pipeline.run_id": ctx.pipeline_run_id or "",
                "pipeline.is_llm": STAGE_REGISTRY[resolve_stage_name(stage)].is_llm
                if resolve_stage_name(stage) in STAGE_REGISTRY
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

    def _with_tail(detail):
        """Anexa tail estruturado ≤8KB ao detail (vira ``output_summary`` no DB)."""
        if not tail.has_events():
            return detail
        merged = dict(detail) if isinstance(detail, dict) else {}
        merged["log_tail"] = tail.as_summary()
        return merged

    obs_logger.info("stage_start", extra={"event": "stage_start"})
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
                # pipeline.success/exit_code em todo caminho — gate de paridade
                # de trace do Caminho 1 (ADR-150 §Consequências, A3.cli.otel).
                if span is not None:
                    span.set_attribute("pipeline.success", ok)
                    span.set_attribute("pipeline.exit_code", 0 if ok else 1)
                obs_logger.info(
                    "stage_end",
                    extra={"event": "stage_end", "duration_ms": round(elapsed), "success": ok},
                )
                return StageResult(
                    stage=stage, success=ok, duration_ms=elapsed, detail=_with_tail(detail)
                )
            except SystemExit as exc:
                elapsed = (time.monotonic() - start) * 1000
                code = exc.code if exc.code is not None else 0
                if span is not None:
                    span.set_attribute("pipeline.success", code == 0)
                    span.set_attribute("pipeline.exit_code", code)
                if code == 0:
                    obs_logger.info(
                        "stage_end",
                        extra={
                            "event": "stage_end",
                            "duration_ms": round(elapsed),
                            "success": True,
                        },
                    )
                    return StageResult(
                        stage=stage, success=True, duration_ms=elapsed, detail={"exit_code": 0}
                    )
                # Stage migrado (logger estruturado): primeiro ERROR do tail é a
                # causa raiz; stderr.last_line vira fallback p/ stages em print.
                error_msg = tail.first_error_message or _extract_error_message(
                    captured_stderr.getvalue(), captured_stdout.getvalue(), code
                )
                obs_logger.error(
                    "stage_error",
                    extra={
                        "event": "stage_error",
                        "duration_ms": round(elapsed),
                        "exit_code": code,
                    },
                )
                return StageResult(
                    stage=stage,
                    success=False,
                    duration_ms=elapsed,
                    detail=_with_tail(None),
                    error=error_msg,
                )
            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                if span is not None:
                    span.record_exception(exc)
                    span.set_attribute("pipeline.success", False)
                    span.set_attribute("pipeline.exit_code", 1)
                obs_logger.error(
                    "stage_error",
                    extra={
                        "event": "stage_error",
                        "duration_ms": round(elapsed),
                        "error_type": type(exc).__name__,
                    },
                )
                return StageResult(
                    stage=stage,
                    success=False,
                    duration_ms=elapsed,
                    detail=_with_tail(None),
                    error=str(exc),
                )
    finally:
        sys.stderr = original_stderr
        sys.stdout = original_stdout
        logging.getLogger("mathoms.pipeline").removeHandler(tail)
        reset_stage(stage_token)


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


if (
    __name__ == "__main__"
):  # pragma: no cover — exercitado por subprocess em tests/test_cli_run_stage.py
    from pipeline.cli_run_stage import main as _cli_main

    raise SystemExit(_cli_main())
