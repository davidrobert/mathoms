"""ADR-441 D2 — a Task base do app Celery redige a falha que tocou o banco.

O `on_failure` era tarde demais: quando ele roda, o Celery já logou a exceção em
`celery.app.trace` e a entregou ao result backend. A base sobrescreve `__call__` — o
tracer a chama no lugar do `run` —, e `autoretry_for`/`self.retry` seguem vendo a
exceção original, porque o retry acontece por dentro dela.

`.apply()` passa pelo tracer, pelo logger de falha e pelo `on_failure`; `.run()` não
passa pelo `__call__` e provaria nada.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.exc import IntegrityError

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.worker import DatabaseFailureRedactingTask, celery_app
from backend.tests.test_falha_de_stage_nao_publica_valor_do_banco import (
    _STAGE,
    _VALORES,
    _unique_violation_com_detail,
    seeded,  # noqa: F401 — fixture reaproveitada
)
from pipeline.observability.failure_text import RedactedDatabaseError

_TENTATIVAS: list[str] = []


@celery_app.task(
    bind=True, name="tests.adr441.retry_sobre_erro_de_banco", max_retries=2, default_retry_delay=0
)
def _retenta_sobre_erro_de_banco(self):
    _TENTATIVAS.append(self.request.id)
    try:
        raise _unique_violation_com_detail()
    except IntegrityError as exc:
        raise self.retry(exc=exc, countdown=0) from exc


class _LogDoTracer(logging.Handler):
    """Guarda o texto que o logger de falha do Celery emitiria, traceback incluído."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.setFormatter(logging.Formatter("%(message)s"))
        self.textos: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.textos.append(self.format(record))


@pytest.fixture
def log_do_tracer(monkeypatch):
    trace_logger = logging.getLogger("celery.app.trace")
    monkeypatch.setattr(trace_logger, "disabled", False)
    handler = _LogDoTracer()
    trace_logger.addHandler(handler)
    yield handler
    trace_logger.removeHandler(handler)


def _kwargs_da_task(seed) -> dict:
    return {
        "run_id": seed["run_id"],
        "ws_id": seed["ws_id"],
        "tenant_root_str": str(seed["tmp_path"]),
        "config_dir_str": str(seed["tmp_path"]),
        "stages": [_STAGE],
        "skip_llm": True,
        "stop_on_error": True,
    }


def _aplica_com_setup_quebrado(seed, erro: BaseException):
    import backend.app.tasks.pipeline_task as task_module

    with patch.object(task_module, "_setup_run_context", side_effect=erro):
        return task_module.run_pipeline_task.apply(kwargs=_kwargs_da_task(seed))


def test_falha_que_tocou_o_banco_sai_redigida_do_tracer(seeded, log_do_tracer):  # noqa: F811
    resultado = _aplica_com_setup_quebrado(seeded, _unique_violation_com_detail())

    assert resultado.state == "FAILURE"
    assert isinstance(resultado.result, RedactedDatabaseError)
    textos = [str(resultado.result), resultado.traceback or "", *log_do_tracer.textos]
    assert not [v for v in _VALORES for t in textos if v in t], textos
    # Não-vácuo: o tracer logou a falha, e o `on_failure` marcou o run.
    assert any("UniqueViolation" in t for t in log_do_tracer.textos)
    with seeded["sync_session"]() as db:
        assert db.get(PipelineRun, seeded["run_id"]).status == PipelineRunStatus.failed


def test_erro_que_nao_e_de_banco_passa_intacto(seeded):  # noqa: F811
    resultado = _aplica_com_setup_quebrado(seeded, ValueError("erro de domínio"))

    assert type(resultado.result) is ValueError
    assert str(resultado.result) == "erro de domínio"


def _prazo_estoura_tratando_erro_de_banco(*_args, **_kwargs):
    try:
        raise _unique_violation_com_detail()
    except IntegrityError:
        raise SoftTimeLimitExceeded()  # noqa: B904 — o contexto implícito é o caso


def test_fim_de_prazo_passa_intacto_mesmo_sobre_erro_de_banco(seeded):  # noqa: F811
    """O tipo é contrato do `on_failure` (`failure_reason=time_limit_exceeded`)."""
    resultado = _aplica_com_setup_quebrado(seeded, _prazo_estoura_tratando_erro_de_banco)

    assert type(resultado.result) is SoftTimeLimitExceeded


def test_self_retry_sobre_erro_de_banco_continua_retentando():
    _TENTATIVAS.clear()
    resultado = _retenta_sobre_erro_de_banco.apply()

    assert len(_TENTATIVAS) == 3  # 1 + max_retries=2: o `Retry` passou intacto pela base
    assert resultado.state == "FAILURE"
    texto = str(resultado.result) + (resultado.traceback or "")
    assert not [v for v in _VALORES if v in texto], texto


def test_toda_task_do_app_herda_a_base_que_redige():
    """A borda é o app inteiro, não o `pipeline.run`: são 14 tasks com o mesmo log de falha."""
    celery_app.loader.import_default_modules()
    tasks = {n: t for n, t in celery_app.tasks.items() if not n.startswith("celery.")}

    assert len(tasks) > 10  # zero seria leitura vazia, não app limpo
    assert {n for n, t in tasks.items() if not isinstance(t, DatabaseFailureRedactingTask)} == set()
