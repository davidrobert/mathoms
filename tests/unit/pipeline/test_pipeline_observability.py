"""Contrato do ``pipeline/observability`` (ADR-273 PR1)."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from pipeline.observability import (
    PipelineJsonFormatter,
    StageLogTail,
    bind,
    get_logger,
    get_run_id,
    get_stage,
    get_trace_id,
    get_workspace_id,
    reset,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _format_record(msg: str = "hello", *, level: int = logging.INFO, **extra) -> dict:
    record = logging.LogRecord("mathoms.pipeline.test", level, "x.py", 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(PipelineJsonFormatter().format(record))


# ---------- Standalone: contextvars vazios degradam limpo (critério 3) ----------


def test_standalone_contextvars_vazios_sem_crash():
    assert get_trace_id() is None
    assert get_workspace_id() is None
    assert get_run_id() is None
    assert get_stage() is None
    payload = _format_record()
    assert payload["message"] == "hello"
    assert "trace_id" not in payload
    assert "workspace_id" not in payload


# ---------- bind/reset com tokens (critério 2 + anti-leak Celery) ----------


def test_bind_propaga_campos_no_log():
    tokens = bind(trace_id="tr-1", workspace_id="ws-1", run_id="run-1")
    try:
        payload = _format_record()
        assert payload["trace_id"] == "tr-1"
        assert payload["workspace_id"] == "ws-1"
        assert payload["pipeline_run_id"] == "run-1"
    finally:
        reset(tokens)


def test_reset_isola_runs_sequenciais_no_mesmo_processo():
    """2 runs no mesmo worker: contexto do run A não vaza pro run B (senior-cto)."""
    tokens_a = bind(trace_id="tr-a", workspace_id="ws-a", run_id="run-a")
    reset(tokens_a)
    assert get_workspace_id() is None, "leak do run A após reset"

    tokens_b = bind(trace_id="tr-b", workspace_id="ws-b", run_id="run-b")
    try:
        payload = _format_record()
        assert payload["workspace_id"] == "ws-b"
        assert payload["trace_id"] == "tr-b"
    finally:
        reset(tokens_b)
    assert get_workspace_id() is None


def test_reset_em_excecao_nao_deixa_residuo():
    tokens = bind(workspace_id="ws-err", run_id="run-err")
    try:
        raise RuntimeError("stage explodiu")
    except RuntimeError:
        pass
    finally:
        reset(tokens)
    assert get_workspace_id() is None
    assert get_run_id() is None


# ---------- Formatter: redação por chave (denylist compartilhada) ----------


def test_formatter_redige_extra_sensivel():
    payload = _format_record(saldo="1234.56", conta_id="abc")
    assert payload["saldo"] == "***"
    assert payload["conta_id"] == "abc"


def test_formatter_redige_dict_aninhado():
    payload = _format_record(detalhe={"valor_total": 10, "count": 3})
    assert payload["detalhe"]["valor_total"] == "***"
    assert payload["detalhe"]["count"] == 3


def test_denylist_backend_e_pipeline_sao_o_mesmo_objeto():
    """Anti-drift (sre-devops): fonte única da denylist."""
    from backend.app.core.logging import SENSITIVE_FIELD_SUBSTRINGS as backend_list
    from pipeline.observability.redaction import SENSITIVE_FIELD_SUBSTRINGS as pipeline_list

    assert backend_list is pipeline_list


# ---------- get_logger: namespace + handler idempotente ----------


def test_get_logger_namespace_e_handler_unico():
    logger_a = get_logger("stages.teste")
    logger_b = get_logger("mathoms.pipeline.stages.teste")
    assert logger_a is logger_b
    root = logging.getLogger("mathoms.pipeline")
    managed = [h for h in root.handlers if getattr(h, "_mathoms_pipeline_managed", False)]
    # ≤1: em suíte com backend setup_logging ativo o handler próprio não é
    # criado (records propagam ao handler do backend com contexto estampado).
    assert len(managed) <= 1
    # Propagação fica ativa — caplog e coexistência com o root dependem disso.
    assert root.propagate is True


def test_get_logger_estampa_contexto_para_propagacao(caplog):
    logger = get_logger("stages.stamp_teste")
    tokens = bind(trace_id="tr-9", workspace_id="ws-9", run_id="run-9", stage="E3")
    try:
        with caplog.at_level(logging.INFO, logger="mathoms.pipeline.stages.stamp_teste"):
            logger.info("stage aggregate", extra={"count": 1})
    finally:
        reset(tokens)
    record = caplog.records[-1]
    assert record.workspace_id == "ws-9"
    assert record.pipeline_run_id == "run-9"
    assert record.trace_id == "tr-9"
    assert record.stage == "E3"


# ---------- StageLogTail (critério 5 + condição sre-devops) ----------


def _make_record(level: int, msg: str) -> logging.LogRecord:
    return logging.LogRecord("mathoms.pipeline.x", level, "x.py", 1, msg, None, None)


def test_tail_preserva_primeiro_error_apos_estouro():
    tail = StageLogTail(max_events=5)
    tail.emit(_make_record(logging.ERROR, "causa raiz"))
    for i in range(20):
        tail.emit(_make_record(logging.WARNING, f"sintoma {i}"))
    summary = tail.as_summary()
    assert tail.first_error_message == "causa raiz"
    assert summary["first_error"] == {"level": "ERROR", "message": "causa raiz"}
    assert len(summary["events"]) == 5
    assert summary["counters"]["WARNING"] == 20
    assert summary["counters"]["ERROR"] == 1


def test_tail_respeita_hard_cap_de_bytes():
    tail = StageLogTail(max_events=50, max_bytes=1024)
    for i in range(50):
        tail.emit(_make_record(logging.WARNING, "x" * 200 + str(i)))
    summary = tail.as_summary()
    assert len(json.dumps(summary, ensure_ascii=False)) <= 1024
    assert summary["counters"]["WARNING"] == 50


def test_tail_vazio_nao_tem_eventos():
    tail = StageLogTail()
    assert not tail.has_events()


# ---------- Gate PII (critério 6) ----------


def test_gate_pii_self_test_passa():
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "dev" / "check_pipeline_log_pii.py"), "--self-test"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_gate_pii_sem_regressao_no_repo():
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "dev" / "check_pipeline_log_pii.py")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
