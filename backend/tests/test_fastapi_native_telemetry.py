"""fastapi ≥0.142 liga OTel nativo por default quando há TracerProvider global — e o
``setup_otel`` sempre registra um. A fonte de instrumentação é a da ADR-110; o app
desliga os emissores nativos pelo construtor (``NATIVE_TELEMETRY_OFF``)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from backend.app.core.otel import NATIVE_TELEMETRY_OFF
from backend.app.main import app

_NATIVE_SCOPE = "fastapi"


@pytest.fixture
def exporter() -> Iterator[InMemorySpanExporter]:
    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider), "setup_otel deveria ter registrado o SDK"
    spans = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(spans))
    yield spans
    spans.shutdown()  # o provider é global: exporter desligado para de acumular


def _native_spans(spans: InMemorySpanExporter) -> list[str]:
    return [
        s.name for s in spans.get_finished_spans() if s.instrumentation_scope.name == _NATIVE_SCOPE
    ]


def _probe_app(**kwargs: object) -> FastAPI:
    probe = FastAPI(**kwargs)

    @probe.get("/probe")
    async def _probe() -> dict[str, str]:
        return {"ok": "1"}

    return probe


def test_app_emits_no_native_fastapi_span(exporter: InMemorySpanExporter) -> None:
    with TestClient(app) as client:
        client.get("/health")
    assert _native_spans(exporter) == []


def test_native_span_detection_is_not_inert(exporter: InMemorySpanExporter) -> None:
    """Contrafactual: com o default do fastapi o escopo nativo aparece; com o OFF, some."""
    TestClient(_probe_app()).get("/probe")
    assert _native_spans(exporter), "default do fastapi deveria emitir span nativo"
    exporter.clear()
    TestClient(_probe_app(telemetry=NATIVE_TELEMETRY_OFF)).get("/probe")
    assert _native_spans(exporter) == []
