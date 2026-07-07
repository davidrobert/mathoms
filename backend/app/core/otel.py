"""OpenTelemetry bootstrap (A6f.3 · ADR-110).

Opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT` env var. When unset, the SDK is
initialized with no exporter so instrumentation still populates trace/span
context into log records (via `LoggingInstrumentor`) without requiring a
collector to be running.
"""

from __future__ import annotations

import logging
import os
from typing import Any

_INSTRUMENTED = False


def is_otel_enabled() -> bool:
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def setup_otel(service_name: str = "mathoms-api") -> None:
    """Initialize OTel SDK + log correlation. Safe to call multiple times."""
    global _INSTRUMENTED
    if _INSTRUMENTED:
        return

    from opentelemetry import trace
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    if is_otel_enabled():
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "OTLP exporter init failed; traces will be in-memory only: %s",
                exc,
            )
        _setup_metrics_exporter(resource)

    trace.set_tracer_provider(provider)

    LoggingInstrumentor().instrument(set_logging_format=False)

    _INSTRUMENTED = True


def _setup_metrics_exporter(resource: Any) -> None:
    """OTLP metrics (A33.l7): ``MeterProvider`` só quando há endpoint — sem ele
    a Metrics API fica no no-op default (zero overhead, mesmo opt-in dos traces)."""
    try:
        from opentelemetry import metrics
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        reader = PeriodicExportingMetricReader(OTLPMetricExporter())
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "OTLP metric exporter init failed; metrics disabled: %s", exc
        )


def instrument_fastapi(app: Any) -> None:
    """Install FastAPI + SQLAlchemy instrumentation on a live app."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "OTel FastAPI/SQLAlchemy instrumentation skipped: %s", exc
        )


def instrument_celery() -> None:
    """Install Celery instrumentation (call from worker bootstrap)."""
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
    except Exception as exc:
        logging.getLogger(__name__).warning("OTel Celery instrumentation skipped: %s", exc)
