"""PipelineService — runs the pipeline via Celery task with DB-tracked progress.

Phase 5 migrou para a fila Celery; a ADR-359 removeu o fallback in-process que
sobrevivia da ADR-014 — o Celery é o único executor, e falha de dispatch é
**alta**. Cancellation is stage-boundary: sets status in DB, task checks between
stages.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.models.llm_config import LLMConfig
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.pipeline.dispatch_contract import CANCELLABLE_STATUSES
from backend.app.services.pipeline.events import publish_run_cancelled
from backend.app.services.pipeline.pipeline_failure_reasons import (
    DISPATCH_FAILED,
    RUN_SETUP_FAILED,
)
from backend.app.services.security.vault import get_vault
from backend.app.services.storage import StorageService

logger = logging.getLogger(__name__)
_vault = get_vault()


class PipelineDispatchError(RuntimeError):
    # `reason` é valor de `pipeline_failure_reasons`; o caller compensa o estado
    # que ele mesmo criou e traduz para a superfície dele (ADR-359 §2).
    """O run não foi entregue a nenhum executor (ADR-359)."""

    def __init__(self, reason: str, run_id: str) -> None:
        self.reason = reason
        self.run_id = run_id
        super().__init__(f"pipeline dispatch failed run={run_id} reason={reason}")


def _redacted_broker_host() -> str:
    """Host:porta do broker sem credencial — ``REDIS_URL`` carrega senha em prod."""
    parts = urlsplit(settings.REDIS_URL)
    return f"{parts.hostname or '?'}:{parts.port or '?'}"


def _classify_llm_config(cfg: LLMConfig | None, ws_id: str, *, context: str) -> str:
    """Shared tier classification with observability for silent-decrypt failures.

    Loga WARNING quando `LLMConfig` existe mas o ciphertext não decripta
    (Fernet key rotacionada / trocada) ou decripta para vazio. Sem isso,
    o pipeline degrada silenciosamente para `free tier` e todos os stages
    LLM (E1, E1.5, E2-llm, E6-parecer) são pulados sem rastro.
    """
    if cfg is None:
        return "free"
    ciphertext = (cfg.api_key_encrypted or "").strip()
    if not ciphertext:
        logger.warning(
            "LLMConfig sem api_key_encrypted ws=%s ctx=%s — degradando para free tier",
            ws_id,
            context,
        )
        return "free"
    try:
        plain = _vault.decrypt(ciphertext)
    except Exception as exc:
        logger.warning(
            "LLMConfig.api_key_encrypted falhou ao decriptar ws=%s ctx=%s err=%s — "
            "FERNET_KEY provavelmente rotacionada; usuário precisa re-adicionar a API key",
            ws_id,
            context,
            exc,
        )
        return "free"
    if not plain or not str(plain).strip():
        logger.warning(
            "LLMConfig.api_key_encrypted decriptou para vazio ws=%s ctx=%s — "
            "FERNET_KEY provavelmente rotacionada; usuário precisa re-adicionar a API key",
            ws_id,
            context,
        )
        return "free"
    return "premium"


def detect_tier(ws_id: str) -> str:
    """``premium`` only when LLMConfig exists and the API key decrypts to non-empty text."""
    with SyncSessionLocal() as db:
        cfg = db.query(LLMConfig).filter(LLMConfig.workspace_id == ws_id).first()
        return _classify_llm_config(cfg, ws_id, context="detect_tier")


async def resolve_llm_tier_async(db: AsyncSession, workspace_id: str) -> str:
    """Async variant of :func:`detect_tier` for FastAPI handlers (same rules)."""
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == workspace_id))
    cfg = result.scalar_one_or_none()
    return _classify_llm_config(cfg, workspace_id, context="resolve_llm_tier_async")


def _dispatch_celery_task(
    run_id: str,
    ws_id: str,
    tenant_root,
    config_dir,
    stages: list[str],
    skip_llm: bool,
    stop_on_error: bool,
    tier: str,
    incremental: bool,
    incremental_doc_paths: list[str] | None,
    base_run_id: str | None = None,
    base_run_fallback_stages: list[str] | None = None,
) -> str:
    from backend.app.tasks.pipeline_task import run_pipeline_task

    task_id = str(uuid.uuid4())
    # ADR-359: persistir ANTES do enqueue faz `celery_task_id IS NULL` significar
    # "dispatch nunca tentado" — invariante do qual a cura de órfão depende. A
    # ordem inversa (delay → write) tornava run legitimamente enfileirado
    # indistinguível de run nunca despachado, e deixava janela em que um cancel
    # não podia revogar a task. O worker reescreve o mesmo id em `_mark_run_started`.
    _persist_celery_task_id(run_id, task_id)
    run_pipeline_task.apply_async(
        kwargs={
            "run_id": run_id,
            "ws_id": ws_id,
            "tenant_root_str": str(tenant_root),
            "config_dir_str": str(config_dir),
            "stages": stages,
            "skip_llm": skip_llm,
            "stop_on_error": stop_on_error,
            "tier": tier,
            "incremental": incremental,
            "incremental_doc_paths": incremental_doc_paths or [],
            "base_run_id": base_run_id,
            "base_run_fallback_stages": base_run_fallback_stages or [],
        },
        task_id=task_id,
    )
    logger.info("Pipeline %s dispatched as Celery task %s", run_id, task_id)
    return task_id


def _persist_celery_task_id(run_id: str, task_id: str) -> None:
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if run is None:
            logger.warning("Pipeline run %s desapareceu antes do dispatch", run_id)
            return
        run.celery_task_id = task_id
        db.commit()


def _prepare_run_context(ws_id: str, tier: str | None) -> tuple[str, object, object]:
    """A7.1 (ADR-134): configs A7.1 fluem via ``WorkspaceContext.config_overrides``;
    aqui só materializamos os fora do escopo (pipeline, llm) + cópia global."""
    from backend.app.services.config_materializer import prepare_pipeline_config_dir

    resolved_tier = tier if tier is not None else detect_tier(ws_id)
    tenant_root = StorageService().ensure_tenant_dirs(ws_id)
    with SyncSessionLocal() as db:
        config_dir = prepare_pipeline_config_dir(ws_id, tenant_root, db)
    return resolved_tier, tenant_root, config_dir


def start_pipeline_run(
    run_id: str,
    ws_id: str,
    stages: list[str],
    *,
    skip_llm: bool = True,
    stop_on_error: bool = True,
    tier: str | None = None,
    incremental: bool = False,
    incremental_doc_paths: list[str] | None = None,
    base_run_id: str | None = None,
    base_run_fallback_stages: list[str] | None = None,
) -> str:
    """Launch the pipeline as a Celery task; returns the Celery task ID.

    Levanta ``PipelineDispatchError`` se o run não foi entregue a nenhum
    executor. **Não** transiciona estado — compensar é do caller que criou o
    estado forward (ADR-359 §2).
    """
    try:
        tier, tenant_root, config_dir = _prepare_run_context(ws_id, tier)
    except Exception as exc:
        _log_dispatch_failure(run_id, ws_id, RUN_SETUP_FAILED, exc)
        raise PipelineDispatchError(RUN_SETUP_FAILED, run_id) from exc
    try:
        return _dispatch_celery_task(
            run_id,
            ws_id,
            tenant_root,
            config_dir,
            stages,
            skip_llm,
            stop_on_error,
            tier,
            incremental,
            incremental_doc_paths,
            base_run_id,
            base_run_fallback_stages,
        )
    except Exception as exc:
        _log_dispatch_failure(run_id, ws_id, DISPATCH_FAILED, exc)
        raise PipelineDispatchError(DISPATCH_FAILED, run_id) from exc


def _log_dispatch_failure(run_id: str, ws_id: str, reason: str, exc: Exception) -> None:
    """``ERROR``, nunca ``CRITICAL``: isto é sintoma; o incidente é 'broker
    degradado', que não é cognoscível daqui (ADR-359 §7). Sem ``str(exc)`` — erro
    de conexão traz a URL do broker, e ``REDIS_URL`` carrega credencial."""
    logger.error(
        "mathoms.pipeline.dispatch_failed run=%s reason=%s error=%s broker=%s",
        run_id,
        reason,
        type(exc).__name__,
        _redacted_broker_host(),
        extra={
            "event": "mathoms.pipeline.dispatch_failed",
            "run_id": run_id,
            "workspace_id": ws_id,
            "failure_reason": reason,
            "broker_error_class": type(exc).__name__,
        },
    )


# A40.l27 — três writes aqui, cada um fechando um defeito medido (co-design `sre-devops`
# 2026-08-07):
#
# (1) `celery_task_id = None`. O id herdado é STALE (do run original, já terminado), e
# deixá-lo não-NULL faria o discriminante de órfão (`celery_task_id IS NULL`, ADR-359 §4)
# nunca casar em `resuming` — a varredura veria o zumbi e o julgaria legítimo. Limpar é
# seguro: `_dispatch_celery_task` grava um id novo antes do enqueue, e revogar a task
# original (terminada) já era no-op.
#
# (2) `last_heartbeat_at = now()` é o relógio de ENTRADA-NO-ESTADO. `started_at` é do run
# original (horas antes), então predicado temporal sobre ele seria sempre verdadeiro e
# mataria resume legítimo na primeira varredura — precisamente a alternativa que a ADR-359
# §Alternativas rejeitou (run legítimo `failed`, worker recusa por terminal, descarte
# silencioso com `failure_reason` mentiroso). É o único relógio durável disponível e é
# lixo estale durante `resuming`; a ADR-172 não colide porque filtra `status='running'`.
#
# (3) `paused_at_stage` PRESERVADO (antes era zerado aqui). A única cópia durável do ponto
# de pausa passava a existir só na memória do processo que morreu. Com a coluna intacta o
# zumbi segue diagnosticável; zerá-la tornava `_stages_after_paused(None)` → `[]` →
# `_mark_run_completed`, i.e. run reportando sucesso sem executar nada.
def _flip_run_to_resuming(run_id: str, ws_id: str) -> tuple[str | None, str]:
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not run or run.workspace_id != ws_id:
            raise ValueError("Run not found")
        if run.status != PipelineRunStatus.needs_review:
            raise ValueError(f"Run is not paused for review (status: {run.status})")

        paused_stage = run.paused_at_stage
        tier = run.tier_at_run or "free"

        run.status = PipelineRunStatus.resuming
        run.celery_task_id = None
        run.last_heartbeat_at = datetime.now(timezone.utc)
        db.commit()
    return paused_stage, tier


def _stages_after_paused(paused_stage: str | None) -> list[str]:
    from pipeline.orchestrator import FULL_ORDER

    if paused_stage and paused_stage in FULL_ORDER:
        idx = FULL_ORDER.index(paused_stage)
        return list(FULL_ORDER[idx + 1 :])
    return []


def _mark_run_completed(run_id: str) -> None:
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        run.status = PipelineRunStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        db.commit()


def resume_pipeline_run(run_id: str, ws_id: str) -> None:
    """Resume a pipeline run paused for review — picks up from the stage *after* paused."""
    paused_stage, tier = _flip_run_to_resuming(run_id, ws_id)
    remaining_stages = _stages_after_paused(paused_stage)

    if not remaining_stages:
        _mark_run_completed(run_id)
        return

    _dispatch_resume(run_id, ws_id, remaining_stages, tier, paused_stage)


def _dispatch_resume(
    run_id: str, ws_id: str, stages: list[str], tier: str, paused_stage: str | None
) -> None:
    """Despacha o resume; em falha de dispatch reverte a pausa em vez de matá-la."""
    try:
        start_pipeline_run(
            run_id=run_id,
            ws_id=ws_id,
            stages=stages,
            skip_llm=False,
            stop_on_error=True,
            tier=tier,
        )
    except PipelineDispatchError:
        # ADR-359 §2: a ação forward aqui foi `needs_review`→`resuming` + zerar
        # `paused_at_stage`. Marcar `failed` (a compensação do trigger)
        # converteria pausa recuperável em run morto com o ponto de pausa
        # perdido — compensar é REVERTER.
        _revert_resuming_to_needs_review(run_id, paused_stage)
        raise


def _revert_resuming_to_needs_review(run_id: str, paused_stage: str | None) -> None:
    """UPDATE condicional em ``status='resuming'`` — no-op se outro ator já avançou."""
    with SyncSessionLocal() as db:
        result = db.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id, PipelineRun.status == PipelineRunStatus.resuming)
            .values(status=PipelineRunStatus.needs_review, paused_at_stage=paused_stage)
        )
        db.commit()
    if result.rowcount != 1:
        logger.warning("Compensação de resume no-op run=%s — status já não era `resuming`", run_id)


def cancel_pipeline_run(run_id: str) -> bool:
    """Signal a running pipeline to cancel (stage-boundary).

    Sets status to cancelled in DB. The Celery task checks between stages.
    Also revokes the Celery task if possible.
    """
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not run:
            return False
        # `resuming` entra aqui (A40.l27): sem isso o órfão de resume não tinha NENHUMA
        # porta de saída — `cancel` recusava e `is_run_active` devolvia True para sempre.
        if run.status not in CANCELLABLE_STATUSES:
            return False

        run.status = PipelineRunStatus.cancelled
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

        celery_task_id = run.celery_task_id

    if celery_task_id:
        try:
            from backend.app.worker import celery_app

            celery_app.control.revoke(celery_task_id, terminate=False)
        except Exception:
            pass

    publish_run_cancelled(run_id)
    return True


def is_run_active(run_id: str) -> bool:
    """Check if a pipeline run is still active."""
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not run:
            return False
        return run.status in (
            PipelineRunStatus.pending,
            PipelineRunStatus.running,
            PipelineRunStatus.resuming,
        )
