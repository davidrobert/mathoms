"""A3.cli.otel (ADR-150 §4, track Fase 2): trace contínuo via ``TRACEPARENT``.

Gates: span do stage nasce filho do trace injetado (W3C context propagation),
com nome ``pipeline.<stage>`` e os 6 attributes canônicos bit-exact; sem
``TRACEPARENT`` o CLI executa normal (span raiz). Testes in-process — o
exporter in-memory não atravessa subprocess; o caminho subprocess real é
coberto por ``tests/test_cli_run_stage.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from pipeline import cli_run_stage

_TRACE_ID_HEX = "0123456789abcdef0123456789abcdef"
_PARENT_SPAN_HEX = "0011223344556677"
_TRACEPARENT = f"00-{_TRACE_ID_HEX}-{_PARENT_SPAN_HEX}-01"
_CANONICAL_ATTRS = {
    "pipeline.stage",
    "pipeline.workspace_root",
    "pipeline.run_id",
    "pipeline.is_llm",
    "pipeline.success",
    "pipeline.exit_code",
}


@pytest.fixture
def in_memory_exporter(monkeypatch):
    """TracerProvider + InMemorySpanExporter (padrão de test_otel_traces.py)."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "mathoms-test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    trace._TRACER_PROVIDER_SET_ONCE._done = False  # type: ignore[attr-defined]
    trace.set_tracer_provider(provider)

    import pipeline.orchestrator as orch

    monkeypatch.setattr(orch, "_TRACER", trace.get_tracer("mathoms.pipeline.orchestrator"))

    yield exporter

    # Teardown volta ao pristine (None) — restaurar o ProxyTracerProvider pré-teste
    # faz o proxy delegar para si mesmo → RecursionError no próximo teste.
    trace._TRACER_PROVIDER_SET_ONCE._done = False  # type: ignore[attr-defined]
    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]


def _ensure_test_fernet_key(monkeypatch) -> None:
    # Hidratação exige o vault Fernet; settings pode ter sido instanciado sem key.
    from backend.app.core.config import settings

    test_key = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="
    monkeypatch.setenv("MATHOMS_FERNET_KEY", test_key)
    if not settings.FERNET_KEY:
        monkeypatch.setattr(settings, "FERNET_KEY", test_key)


def _isolate_redis(monkeypatch) -> None:
    # Caches da hidratação (catálogo/budget) não podem escrever no Redis dev:
    # aponta o client para porta fechada (fail-open) e zera o singleton.
    from backend.app.core.config import settings
    from backend.app.services import events

    monkeypatch.setattr(settings, "REDIS_URL", "redis://127.0.0.1:6390/0")
    monkeypatch.setattr(events, "_redis_client", None)


def _patch_in_memory_store(monkeypatch):
    """Aponta as factories de sessão (artifact + config) para SQLite em memória."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import backend.app.models  # noqa: F401 — registra tabelas no metadata
    from backend.app.core.database import Base
    from backend.app.services import artifact_session_factory as factory
    from backend.app.services import run_context_factory

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(factory, "_new_session_or_raise", lambda: session_factory())
    monkeypatch.setattr(run_context_factory, "_default_session_factory", lambda: session_factory())
    monkeypatch.setenv("MATHOMS_DATABASE_URL", "sqlite+aiosqlite://in-memory-via-fixture")
    _ensure_test_fernet_key(monkeypatch)
    _isolate_redis(monkeypatch)
    return engine


def _run_stage_cli_args(tmp_path: Path, run_id: str) -> list[str]:
    workspace = ["--workspace", str(tmp_path), "--run-id", run_id, "--workspace-id", "ws-otel"]
    return ["run-stage", "reconcile_transactions", *workspace]


@pytest.fixture
def cli_in_process(tmp_path: Path, monkeypatch):
    """Chama ``main()`` in-process: store em SQLite memória + runner fake."""
    import pipeline.orchestrator as orch

    engine = _patch_in_memory_store(monkeypatch)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(orch, "_get_stage_runner", lambda stage: lambda ctx: {"ok": True})

    def run(run_id: str) -> int:
        return cli_run_stage.main(_run_stage_cli_args(tmp_path, run_id))

    yield run
    engine.dispose()


def _single_stage_span(exporter):
    spans = [s for s in exporter.get_finished_spans() if s.name.startswith("pipeline.")]
    assert len(spans) == 1, [s.name for s in spans]
    return spans[0]


def test_traceparent_creates_child_span_with_canonical_attrs(
    in_memory_exporter, cli_in_process, monkeypatch, capsys, tmp_path
):
    monkeypatch.setenv("TRACEPARENT", _TRACEPARENT)

    rc = cli_in_process("r-otel")

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["success"] is True
    span = _single_stage_span(in_memory_exporter)
    assert span.name == "pipeline.reconcile_transactions"
    assert span.context.trace_id == int(_TRACE_ID_HEX, 16), "trace-id != o injetado"
    assert span.parent is not None and span.parent.span_id == int(_PARENT_SPAN_HEX, 16)
    assert _CANONICAL_ATTRS <= set(span.attributes), sorted(span.attributes)
    assert span.attributes["pipeline.stage"] == "reconcile_transactions"
    assert span.attributes["pipeline.workspace_root"] == str(tmp_path.resolve())
    assert span.attributes["pipeline.run_id"] == "r-otel"
    assert span.attributes["pipeline.is_llm"] is False
    assert span.attributes["pipeline.success"] is True
    assert span.attributes["pipeline.exit_code"] == 0


def test_without_traceparent_cli_runs_with_root_span(
    in_memory_exporter, cli_in_process, monkeypatch, capsys
):
    monkeypatch.delenv("TRACEPARENT", raising=False)

    rc = cli_in_process("r-sem-trace")

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["success"] is True
    span = _single_stage_span(in_memory_exporter)
    assert span.parent is None, "sem TRACEPARENT o span deve ser raiz"
    assert _CANONICAL_ATTRS <= set(span.attributes)


def test_malformed_traceparent_never_crashes(
    in_memory_exporter, cli_in_process, monkeypatch, capsys
):
    monkeypatch.setenv("TRACEPARENT", "lixo-invalido")

    rc = cli_in_process("r-malformado")

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["success"] is True
