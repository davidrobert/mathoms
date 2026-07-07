"""Métricas OTLP ``mathoms.llm.*`` com exporter in-memory (A33.l7 · ADR-110).

Cobre as 4 métricas da lane com labels compostos ``{prompt_name, prompt_version}``:
confidence (histogram → p50/p95 no backend de métricas), needs_review_rate
(needs_review/calls), cache_hit_rate (hits/misses) e parecer.riscos_truncados.
Opt-in preservado: sem ``OTEL_EXPORTER_OTLP_ENDPOINT`` o emitter é ``None``.
"""

from __future__ import annotations

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

import backend.app.core.llm_metrics as llm_metrics_mod
from backend.app.core.llm_metrics import OtelLLMMetrics, get_llm_metrics_emitter

_LABELS = {"prompt_name": "e15_baseline", "prompt_version": "1.2.0"}


@pytest.fixture()
def reader_and_emitter():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    emitter = OtelLLMMetrics(meter_provider=provider)
    yield reader, emitter
    provider.shutdown()


def _metrics_by_name(reader: InMemoryMetricReader) -> dict[str, object]:
    data = reader.get_metrics_data()
    scopes = [sm for rm in data.resource_metrics for sm in rm.scope_metrics]
    return {metric.name: metric for sm in scopes for metric in sm.metrics}


def _points(metric) -> list:
    return list(metric.data.data_points)


def test_confidence_histogram_com_labels_compostos(reader_and_emitter) -> None:
    reader, emitter = reader_and_emitter
    emitter.record_call_quality(**_LABELS, model="claude-test", confidence=0.83, needs_review=False)

    metric = _metrics_by_name(reader)["mathoms.llm.confidence"]
    (point,) = _points(metric)
    assert point.sum == pytest.approx(0.83)
    assert point.count == 1
    attrs = dict(point.attributes)
    assert attrs["prompt_name"] == "e15_baseline"
    assert attrs["prompt_version"] == "1.2.0"
    assert attrs["model"] == "claude-test"
    # Boundaries de [0,1] (não a escala default de latência) — p50/p95 utilizáveis.
    assert 0.7 in point.explicit_bounds and 0.8 in point.explicit_bounds


def test_needs_review_rate_counters(reader_and_emitter) -> None:
    reader, emitter = reader_and_emitter
    emitter.record_call_quality(**_LABELS, model="m", confidence=0.9, needs_review=False)
    emitter.record_call_quality(**_LABELS, model="m", confidence=0.4, needs_review=True)

    by_name = _metrics_by_name(reader)
    (calls,) = _points(by_name["mathoms.llm.calls"])
    (needs_review,) = _points(by_name["mathoms.llm.needs_review"])
    assert calls.value == 2  # denominador
    assert needs_review.value == 1  # numerador → rate 0.5 no backend
    assert dict(needs_review.attributes)["prompt_name"] == "e15_baseline"
    assert dict(needs_review.attributes)["prompt_version"] == "1.2.0"


def test_confidence_none_nao_registra_histogram(reader_and_emitter) -> None:
    reader, emitter = reader_and_emitter
    emitter.record_call_quality(**_LABELS, model="m", confidence=None, needs_review=False)

    by_name = _metrics_by_name(reader)
    confidence = by_name.get("mathoms.llm.confidence")
    assert confidence is None or not _points(confidence)  # sem record → sem data point
    (calls,) = _points(by_name["mathoms.llm.calls"])
    assert calls.value == 1


def test_cache_hit_rate_counters(reader_and_emitter) -> None:
    reader, emitter = reader_and_emitter
    emitter.record_cache_lookup(hit=False, **_LABELS)
    emitter.record_cache_lookup(hit=True, **_LABELS)
    emitter.record_cache_lookup(hit=True, **_LABELS)

    by_name = _metrics_by_name(reader)
    (hits,) = _points(by_name["mathoms.llm.cache_hits"])
    (misses,) = _points(by_name["mathoms.llm.cache_misses"])
    assert hits.value == 2 and misses.value == 1  # rate = 2/3 no backend
    assert dict(hits.attributes) == _LABELS


def test_parecer_riscos_truncados_counter(reader_and_emitter) -> None:
    reader, emitter = reader_and_emitter
    emitter.record_riscos_truncados(
        dropped=3, prompt_name="parecer_planejador", prompt_version="2.1.0"
    )

    metric = _metrics_by_name(reader)["mathoms.llm.parecer.riscos_truncados"]
    (point,) = _points(metric)
    assert point.value == 3
    assert dict(point.attributes) == {
        "prompt_name": "parecer_planejador",
        "prompt_version": "2.1.0",
    }


def test_opt_in_sem_endpoint_retorna_none(monkeypatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(llm_metrics_mod, "_EMITTER_SINGLETON", None)

    assert get_llm_metrics_emitter() is None


def test_opt_in_com_endpoint_singleton_idempotente(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    monkeypatch.setattr(llm_metrics_mod, "_EMITTER_SINGLETON", None)

    first = get_llm_metrics_emitter()
    second = get_llm_metrics_emitter()

    assert isinstance(first, OtelLLMMetrics)
    assert first is second  # lazy singleton idempotente (ADR-111 caso b)
