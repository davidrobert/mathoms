"""Métricas OTLP no choke-point LLM — protocol injetado (A33.l7, ADR-110).

``pipeline/**`` não importa opentelemetry nem backend (``check_pipeline_boundaries``);
o backend injeta a implementação concreta (``OtelLLMMetrics``) via
``WorkspaceContext.llm_metrics_emitter`` — mesmo padrão de ``LLMCallHooks``
(ADR-173) e ``LLMResponseCache`` (ADR-307). ``None`` = no-op (opt-in ADR-110:
sem ``OTEL_EXPORTER_OTLP_ENDPOINT``, zero overhead).

Labels compostos ``{prompt_name, prompt_version}`` (PLAN-llm-prompts-hardening
§decisão 2): ``prompt_name`` é a coordenada de dimensão (ex. ``e15_baseline``),
``prompt_version`` a de tempo (semver puro, ADR-233) — nunca slug embutido na
string de versão.
"""

from __future__ import annotations

import logging
from types import ModuleType
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


class LLMMetricsEmitter(Protocol):
    """Contrato injetado no ``LLMService`` — implementado pelo backend (OTLP)."""

    def record_call_quality(
        self,
        *,
        prompt_name: str,
        prompt_version: str,
        model: str,
        confidence: Optional[float],
        needs_review: bool,
    ) -> None:
        """Pós-call validado: histogram de confidence + counters de call/needs_review."""
        ...

    def record_cache_lookup(self, *, hit: bool, prompt_name: str, prompt_version: str) -> None:
        """Lookup do cache de resposta (ADR-307): counter de hit ou miss."""
        ...

    def record_riscos_truncados(
        self, *, dropped: int, prompt_name: str, prompt_version: str
    ) -> None:
        """Riscos dropados no boundary do parecer (>cap 12) — calibra o cap."""
        ...


def output_quality(output: Any) -> tuple[Optional[float], bool]:
    """``(confidence, needs_review)`` quando o schema declara; ``(None, False)`` senão."""
    confidence = getattr(output, "confidence", None)
    return (
        float(confidence) if confidence is not None else None,
        bool(getattr(output, "needs_review", False)),
    )


def prompt_name_of(prompt_mod: ModuleType) -> str:
    """Nome canônico do prompt = nome do módulo em ``pipeline/llm/prompts/``."""
    return prompt_mod.__name__.rsplit(".", 1)[-1]


def _warn_emit_failed(event: str, prompt_name: str, exc: Exception) -> None:
    """Telemetria nunca derruba a call que já custou tokens (política ADR-173)."""
    logger.warning(
        "LLM metric emit failed",
        extra={"event": event, "prompt_name": prompt_name, "error": str(exc)[:200]},
    )


def emit_call_quality(
    output: Any,
    *,
    emitter: Optional[LLMMetricsEmitter] = None,
    prompt_name: Optional[str],
    prompt_version: Optional[str],
    model: str,
) -> None:
    """Emissão best-effort pós-call validado — falha nunca derruba a call."""
    if emitter is None:
        return
    name = prompt_name or "unknown"
    labels = {"prompt_name": name, "prompt_version": prompt_version or "unversioned"}
    confidence, needs_review = output_quality(output)
    try:
        emitter.record_call_quality(
            model=model, confidence=confidence, needs_review=needs_review, **labels
        )
    except Exception as metrics_exc:
        _warn_emit_failed("call_quality", name, metrics_exc)


def emit_cache_lookup(
    *,
    emitter: Optional[LLMMetricsEmitter] = None,
    hit: bool,
    prompt_name: Optional[str],
    prompt_version: Optional[str],
) -> None:
    """Counter best-effort de cache hit/miss (ADR-307 §D5 + A33.l7)."""
    if emitter is None:
        return
    name = prompt_name or "unknown"
    try:
        emitter.record_cache_lookup(
            hit=hit, prompt_name=name, prompt_version=prompt_version or "unversioned"
        )
    except Exception as metrics_exc:
        _warn_emit_failed("cache_lookup", name, metrics_exc)
