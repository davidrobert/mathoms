"""Contract tests do pipeline-service (B2 do GO_PORT_DEPS §6, plano GO_SHELL).

Congela o contrato HTTP que o shell Go do Caminho 1 (ADR-150) vai honrar:
schemathesis gera casos válidos e negativos a partir do snapshot OpenAPI
(``docs/reference/api/v1/pipeline-service.openapi.json`` — fonte de verdade,
sync garantido por ``test_openapi_snapshot.py``) e valida status codes +
schema de resposta contra a app ASGI in-process (zero rede).

Determinismo (anti-flake, exigência sre-devops): ``derandomize`` + deadline
None + ``max_examples`` baixo. A execução real de stage é fake (o alvo é o
contrato, não o stage — execução real: ``test_artifact_store_integration``);
o 503 tem gatilho não-fuzzável e é coberto por ``test_store_unavailable_returns_503``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import schemathesis
from app.main import create_app
from hypothesis import HealthCheck, settings

_SNAPSHOT = (
    Path(__file__).resolve().parent.parent.parent
    / "docs"
    / "reference"
    / "api"
    / "v1"
    / "pipeline-service.openapi.json"
)

# FastAPI emite OpenAPI 3.1 — suporte no schemathesis 3.x é opt-in.
schemathesis.experimental.OPEN_API_3_1.enable()

schema = schemathesis.from_path(str(_SNAPSHOT), app=create_app())


def _fake_stage(stage, req):
    from app.contracts.stages import StageExecuteResponse

    return StageExecuteResponse(stage=stage, success=True, duration_ms=1.0)


def _fake_run(req):
    from app.contracts.runs import RunSummaryResponse

    return RunSummaryResponse(
        run_id=req.run_id,
        workspace_id=req.workspace_id,
        success=True,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        stages=[],
        failed_stage=None,
    )


@pytest.fixture(autouse=True)
def _fake_execution(monkeypatch):
    """Fuzz não executa stage real (o alvo é o contrato) — fake no boundary route→executor."""
    # Sem isto, payloads válidos disparariam hidratação + ensure_dirs em
    # workspace_root arbitrário (diretórios aleatórios no disco) + stage real.
    from app.api import runs as runs_module
    from app.api import stages as stages_module

    monkeypatch.setattr(stages_module, "run_stage_by_name", _fake_stage)
    monkeypatch.setattr(runs_module, "run_sequence", _fake_run)


@schema.parametrize()
@settings(
    max_examples=12,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)
def test_api_matches_frozen_contract(case):
    response = case.call()
    case.validate_response(response)
