"""Métricas OTLP ``mathoms.llm.*`` — implementação de ``LLMMetricsEmitter`` (A33.l7).

Implementação backend do protocol ``pipeline.llm.metrics.LLMMetricsEmitter``,
injetada em ``WorkspaceContext.llm_metrics_emitter`` por ``run_context_factory``
(mesmo padrão de ``LLMBudgetService``/ADR-173 e ``RedisLLMCache``/ADR-307).

Opt-in ADR-110: ``get_llm_metrics_emitter()`` retorna ``None`` sem
``OTEL_EXPORTER_OTLP_ENDPOINT`` — o choke-point vira no-op, zero overhead.
Labels sempre ``{prompt_name, prompt_version}`` (+ ``model`` na qualidade da
call) — nunca payload, nunca slug embutido na string de versão.

Rates são visão do backend de métricas (Prometheus/Grafana):
``needs_review_rate = needs_review / calls``;
``cache_hit_rate = cache_hits / (cache_hits + cache_misses)``.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.app.core.otel import is_otel_enabled

#: Boundaries do histogram de confidence — resolução fina em [0.5, 1.0] onde
#: vivem os thresholds de produto (0.7 needs_review / 0.8 LLM fallback, ADR-081).
#: Default do SDK é escala de latência (0, 5, 10, 25...) — inútil para [0, 1].
_CONFIDENCE_BUCKETS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]

_RISCOS_METRIC = "mathoms.llm.parecer.riscos_truncados"


def _confidence_histogram(meter: Any) -> Any:
    return meter.create_histogram(
        "mathoms.llm.confidence",
        unit="1",
        description="Confidence declarada pelo output do prompt (p50/p95 no backend)",
        explicit_bucket_boundaries_advisory=_CONFIDENCE_BUCKETS,
    )


def _counter(meter: Any, name: str, description: str) -> Any:
    return meter.create_counter(name, unit="1", description=description)


class OtelLLMMetrics:
    """Instrumentos ``mathoms.llm.*`` sobre a OTel Metrics API — sem ``MeterProvider`` real configurado (``setup_otel`` sem endpoint) tudo é no-op por contrato da API."""

    def __init__(self, meter_provider: Optional[Any] = None) -> None:
        from opentelemetry import metrics

        provider = meter_provider or metrics.get_meter_provider()
        meter = provider.get_meter("mathoms.llm")
        self._confidence = _confidence_histogram(meter)
        self._calls = _counter(meter, "mathoms.llm.calls", "Calls LLM validadas (denominador)")
        self._needs_review = _counter(meter, "mathoms.llm.needs_review", "needs_review=true")
        self._cache_hits = _counter(meter, "mathoms.llm.cache_hits", "Cache hits (ADR-307)")
        self._cache_misses = _counter(meter, "mathoms.llm.cache_misses", "Cache misses (ADR-307)")
        self._riscos_truncados = _counter(meter, _RISCOS_METRIC, "Riscos dropados no cap 12")

    def record_call_quality(
        self,
        *,
        prompt_name: str,
        prompt_version: str,
        model: str,
        confidence: Optional[float],
        needs_review: bool,
    ) -> None:
        labels = {"prompt_name": prompt_name, "prompt_version": prompt_version, "model": model}
        self._calls.add(1, labels)
        if confidence is not None:
            self._confidence.record(confidence, labels)
        if needs_review:
            self._needs_review.add(1, labels)

    def record_cache_lookup(self, *, hit: bool, prompt_name: str, prompt_version: str) -> None:
        labels = {"prompt_name": prompt_name, "prompt_version": prompt_version}
        (self._cache_hits if hit else self._cache_misses).add(1, labels)

    def record_riscos_truncados(
        self, *, dropped: int, prompt_name: str, prompt_version: str
    ) -> None:
        labels = {"prompt_name": prompt_name, "prompt_version": prompt_version}
        self._riscos_truncados.add(dropped, labels)


# Singleton lazy idempotente (ADR-111 exceção b — registrado em
# docs/reference/STATELESS_AUDIT.md §2): mesma env produz o mesmo emitter em
# qualquer worker; instrumentos OTel são thread-safe por contrato do SDK.
_EMITTER_SINGLETON: Optional[OtelLLMMetrics] = None


def get_llm_metrics_emitter() -> Optional[OtelLLMMetrics]:
    """Emitter OTLP ou ``None`` quando o opt-in ADR-110 está desligado."""
    global _EMITTER_SINGLETON
    if not is_otel_enabled():
        return None
    if _EMITTER_SINGLETON is None:
        _EMITTER_SINGLETON = OtelLLMMetrics()
    return _EMITTER_SINGLETON
