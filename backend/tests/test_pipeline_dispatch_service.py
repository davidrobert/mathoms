"""ADR-359 — contrato de dispatch do `pipeline_service` + compensação do resume."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import patch

import pytest

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.pipeline import pipeline_service
from backend.app.services.pipeline.pipeline_failure_reasons import (
    DISPATCH_FAILED,
    RUN_SETUP_FAILED,
)

_PREPARE = "backend.app.services.pipeline.pipeline_service._prepare_run_context"
_DISPATCH = "backend.app.services.pipeline.pipeline_service._dispatch_celery_task"


#: Argumentos posicionais mínimos de `_dispatch_celery_task`.
_DISPATCH_ARGS = (
    "run-1",
    "ws-1",
    "/tmp/x",
    "/tmp/c",
    ["extract_members"],
    True,
    True,
    "free",
    False,
    None,
)


class _RecordingTask:
    """Celery task fake que anota quando o enqueue aconteceu."""

    def __init__(self, order: list[str]) -> None:
        self._order = order

    def apply_async(self, **kwargs) -> None:
        self._order.append("enqueue")


def _resume_patches(reverted: list[tuple[str, str | None]]) -> list:
    """Isola `resume_pipeline_run` do DB, anotando a reversão que ele pedir."""
    return [
        patch.object(
            pipeline_service,
            "_flip_run_to_resuming",
            return_value=("reconcile_transactions", "free"),
        ),
        patch.object(
            pipeline_service,
            "_revert_resuming_to_needs_review",
            side_effect=lambda rid, stage: reverted.append((rid, stage)),
        ),
        patch.object(
            pipeline_service,
            "start_pipeline_run",
            side_effect=pipeline_service.PipelineDispatchError(DISPATCH_FAILED, "run-1"),
        ),
    ]


def test_start_pipeline_run_raises_instead_of_degrading_to_a_thread():
    """A regressão original: falha de dispatch era engolida e virava thread daemon."""
    with patch(_PREPARE, return_value=("free", "/tmp/x", "/tmp/c")):
        with patch(_DISPATCH, side_effect=OSError("Connection refused")):
            with pytest.raises(pipeline_service.PipelineDispatchError) as exc:
                pipeline_service.start_pipeline_run("run-1", "ws-1", ["extract_members"])
    assert exc.value.reason == DISPATCH_FAILED


def test_run_setup_failure_is_a_distinct_reason():
    """`_prepare_run_context` está DENTRO do try — era a segunda porta do órfão."""
    with patch(_PREPARE, side_effect=RuntimeError("config materializer explodiu")):
        with pytest.raises(pipeline_service.PipelineDispatchError) as exc:
            pipeline_service.start_pipeline_run("run-1", "ws-1", ["extract_members"])
    assert exc.value.reason == RUN_SETUP_FAILED


def test_no_thread_fallback_symbol_survives():
    """Gate de arqueologia: o símbolo removido não volta por merge distraído."""
    assert not hasattr(pipeline_service, "_start_fallback_thread")


def test_broker_host_is_redacted():
    """`REDIS_URL` carrega credencial em prod; o log de falha nunca vê `str(exc)`."""
    url = "redis://:sup3rs3cr3t@redis.internal:6379/0"
    with patch.object(pipeline_service.settings, "REDIS_URL", url):
        rendered = pipeline_service._redacted_broker_host()
    assert rendered == "redis.internal:6379"
    assert "sup3rs3cr3t" not in rendered


# Se o enqueue rodasse antes da escrita, run legitimamente enfileirado ficaria
# indistinguível de run nunca despachado — e a cura de órfão marcaria `failed`
# trabalho que estava só esperando fila.
def test_task_id_is_persisted_before_enqueue():
    """Ordem invertida (ADR-359 §4): `celery_task_id IS NULL` ⇒ dispatch nunca tentado."""
    order: list[str] = []
    fake_module = type("M", (), {"run_pipeline_task": _RecordingTask(order)})
    with (
        patch.dict("sys.modules", {"backend.app.tasks.pipeline_task": fake_module}),
        patch.object(
            pipeline_service,
            "_persist_celery_task_id",
            side_effect=lambda *_: order.append("persist"),
        ),
    ):
        task_id = pipeline_service._dispatch_celery_task(*_DISPATCH_ARGS)
    assert order == ["persist", "enqueue"]
    assert task_id


# `_flip_run_to_resuming` já zerou `paused_at_stage` — marcar `failed` (a
# compensação do trigger) perderia o ponto de retomada, convertendo pausa
# recuperável em run morto. Compensação genérica no service faria exatamente isso.
def test_resume_dispatch_failure_reverts_the_pause_instead_of_killing_it():
    """Falha de dispatch no resume REVERTE a pausa, restaurando `paused_at_stage`."""
    reverted: list[tuple[str, str | None]] = []
    with ExitStack() as stack:
        for cm in _resume_patches(reverted):
            stack.enter_context(cm)
        with pytest.raises(pipeline_service.PipelineDispatchError):
            pipeline_service.resume_pipeline_run("run-1", "ws-1")
    assert reverted == [("run-1", "reconcile_transactions")]


def test_revert_targets_only_resuming_status():
    """UPDATE condicional: se outro ator já avançou o run, a reversão é no-op."""
    import inspect

    source = inspect.getsource(pipeline_service._revert_resuming_to_needs_review)
    assert "PipelineRunStatus.resuming" in source
    assert "rowcount" in source


def test_pipeline_run_status_vocabulary_unchanged():
    """A decisão não introduz status novo — só `failure_reason` (String, aberto)."""
    assert PipelineRunStatus.failed.value == "failed"
    assert hasattr(PipelineRun, "failure_reason")
