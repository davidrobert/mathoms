"""Regressão UX: stage_log.errors propaga erros per-doc quando stage retorna soft-fail ``{"success": false, "errors": [{file, error}]}`` (extract_comprovantes_bens, E2-llm, E5.N etc.). Sem isso, UI mostra fallback genérico "lendo os dados" e "Ver detalhes técnicos" exibe tela vazia (incidente prod 2026-05-22, workspace 5@5.com)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from backend.app.models.pipeline_run import PipelineStageStatus
from backend.app.tasks.pipeline_task import (
    _record_stage_result,
    _summarize_per_doc_errors,
)

# ───────────────────────── helper puro ────────────────────────────────────


def test_summarize_returns_none_for_non_dict():
    assert _summarize_per_doc_errors(None) is None
    assert _summarize_per_doc_errors("oops") is None
    assert _summarize_per_doc_errors(42) is None


def test_summarize_returns_none_when_no_errors_key():
    assert _summarize_per_doc_errors({"success": True}) is None
    assert _summarize_per_doc_errors({"errors": []}) is None
    assert _summarize_per_doc_errors({"errors": None}) is None


def test_summarize_formats_file_and_error_per_line():
    detail = {
        "success": False,
        "errors": [
            {"file": "apolice_a.pdf", "error": "LLMService.call() got unexpected kwarg 'model'"},
            {"file": "apolice_b.pdf", "error": "LLMService.call() got unexpected kwarg 'model'"},
        ],
    }
    out = _summarize_per_doc_errors(detail)
    assert out is not None
    assert "apolice_a.pdf:" in out
    assert "apolice_b.pdf:" in out
    assert "unexpected kwarg" in out
    assert out.count("\n") == 1  # 2 lines = 1 newline


def test_summarize_handles_missing_keys_gracefully():
    detail = {"errors": [{"file": "x.pdf"}, {"error": "no file"}, {}]}
    out = _summarize_per_doc_errors(detail)
    assert "x.pdf:" in out
    assert "?: no file" in out
    assert "?: " in out


def test_summarize_handles_string_entries():
    detail = {"errors": ["plain string error", "another"]}
    out = _summarize_per_doc_errors(detail)
    assert out == "plain string error\nanother"


def test_summarize_truncates_at_2000_chars():
    detail = {"errors": [{"file": f"f{i}.pdf", "error": "x" * 100} for i in range(50)]}
    out = _summarize_per_doc_errors(detail)
    assert out is not None
    assert len(out) <= 2000


# ───────────────────────── e2e _record_stage_result ────────────────────────


@dataclass
class _FakeStageResult:
    """Mimics StageResult from pipeline.orchestrator — relevant fields only."""

    success: bool
    detail: Any
    error: str | None = None


def _make_engine_and_session(tmp_path: Path):
    """File-based SQLite — multi-connection seguro (sync engine + sessionmaker)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import backend.app.models  # noqa: F401 — popula metadata
    from backend.app.core.database import Base, attach_sqlite_pragmas

    db_file = tmp_path / "soft_fail.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    attach_sqlite_pragmas(engine)
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine, future=True)
    return SL, SL()


def _seed_run_with_running_stage(session) -> tuple[str, str, str]:
    from backend.app.models import PipelineRun, PipelineStageLog, User, Workspace

    uid, wid = str(uuid.uuid4()), str(uuid.uuid4())
    session.add(
        User(id=uid, email=f"sf-{uuid.uuid4().hex[:8]}@t.co", hashed_password="x", full_name="T")
    )
    session.add(Workspace(id=wid, name="WS", owner_id=uid))
    run = PipelineRun(workspace_id=wid)
    session.add(run)
    session.flush()
    log = PipelineStageLog(
        pipeline_run_id=run.id,
        stage="extract_comprovantes_bens",
        status=PipelineStageStatus.running,
    )
    session.add(log)
    session.commit()
    return run.id, log.id, wid


@pytest.fixture
def _silence_publish(monkeypatch):
    """Eventos pub/sub não importam aqui — silenciar para isolar DB."""
    for name in (
        "publish_stage_completed",
        "publish_stage_failed",
        "publish_needs_review",
        "publish_stage_started",
    ):
        monkeypatch.setattr(f"backend.app.tasks.pipeline_task.{name}", lambda *a, **kw: None)


def _run_and_get_log(tmp_path, monkeypatch, *, result, stage="stage_x"):
    """Roda ``_record_stage_result`` contra SQLite isolado e retorna o ``PipelineStageLog``."""
    from backend.app.models import PipelineStageLog
    from pipeline.stage_outcome import resolve_stage_outcome

    SL, db = _make_engine_and_session(tmp_path)
    run_id, log_id, _ = _seed_run_with_running_stage(db)
    monkeypatch.setattr("backend.app.tasks.pipeline_task.SyncSessionLocal", SL)
    # Deriva o desfecho como o loop faz (A40.l18) em vez de fixar `failed`: assim
    # o teste continua exercitando a disposição real, e um stage que virasse
    # `degradable` mudaria estas asserções em vez de passar por vacuidade.
    outcome = resolve_stage_outcome(stage, delivered=bool(result.success))
    _record_stage_result(run_id, stage, log_id, result, 100, 50, outcome)
    db.expire_all()
    return db.get(PipelineStageLog, log_id)


def test_record_stage_result_populates_errors_from_per_doc_soft_fail(
    tmp_path, monkeypatch, _silence_publish
):
    """Soft-fail dict com errors[] → stage_log.errors recebe sumário (UI deixa de mostrar fallback genérico)."""
    detail = {
        "success": False,
        "processed": [{"file": "ok.pdf"}],
        "errors": [
            {"file": "broken.pdf", "error": "LLMService.call() got unexpected kwarg 'model'"}
        ],
    }
    result = _FakeStageResult(success=False, error=None, detail=detail)
    log = _run_and_get_log(tmp_path, monkeypatch, result=result, stage="extract_comprovantes_bens")
    assert log.status == PipelineStageStatus.failed
    assert log.errors is not None
    assert "broken.pdf:" in log.errors
    assert "unexpected kwarg" in log.errors


def test_record_stage_result_exception_takes_priority_over_per_doc(
    tmp_path, monkeypatch, _silence_publish
):
    """``result.error`` (exception) prevalece sobre ``detail.errors[]`` — comportamento existente preservado."""
    result = _FakeStageResult(
        success=False,
        error="hard exception from orchestrator",
        detail={"errors": [{"file": "x.pdf", "error": "soft fail msg"}]},
    )
    log = _run_and_get_log(tmp_path, monkeypatch, result=result)
    assert log.errors == "hard exception from orchestrator"
    assert "soft fail msg" not in log.errors


def test_record_stage_result_success_leaves_errors_null(tmp_path, monkeypatch, _silence_publish):
    """Stage com success=True não preenche errors mesmo que detail.errors exista (defensivo)."""
    monkeypatch.setattr(
        "backend.app.tasks.pipeline_task._persist_planner_review_if_applicable",
        lambda *a, **kw: None,
    )
    result = _FakeStageResult(success=True, error=None, detail={"success": True})
    log = _run_and_get_log(tmp_path, monkeypatch, result=result)
    assert log.status == PipelineStageStatus.completed
    assert log.errors is None
