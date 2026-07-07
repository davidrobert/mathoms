"""Task Celery beat — drift nightly do ``extract_with_llm`` (A33.l5 · ADR-307 F2).

Roda fora de pico (03:15 BRT / 06:15 UTC — beat em ``worker.py``). CI de PR
nunca chama Anthropic: testes injetam fake em ``_execute_drift_check``; a key
real vem do env do worker (``ANTHROPIC_API_KEY``), sem secret novo.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

from backend.app.core.logging import get_logger
from backend.app.services.extract_llm_drift import (
    DRIFT_STAGE,
    FixtureDriftResult,
    StructuredLLMClient,
    persist_drift_results,
    run_extract_llm_drift,
)
from backend.app.worker import celery_app

logger = logging.getLogger(__name__)
_drift_metrics = get_logger("llm.drift")

_WORKSPACE_ENV = "MATHOMS_LLM_DRIFT_WORKSPACE_ID"

# Custo por execução (medido na 1ª execução real, 2026-07-07): 4 fixtures ×
# 1 trial em claude-sonnet (~2k tokens in / ~0,5k out por call) ≈ US$0,07/noite
# → ≈ US$2,10/mês-calendário, somando ao dogfood no MESMO cap ADR-173
# (default US$20/mês). O hard-stop pré-call (110%) curto-circuita o batch —
# o job nunca é quem estoura o cap e silencia extração real.


@celery_app.task(name="fin.llm.detect_extract_llm_drift", bind=True, max_retries=0)
def detect_extract_llm_drift(self) -> dict[str, Any]:
    """Drift estrutural nightly do extract_with_llm — 1 trial/fixture; ~US$0,07/execução (cap ADR-173)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return _skipped("ANTHROPIC_API_KEY missing")

    workspace_id = _resolve_drift_workspace()
    if workspace_id is None:
        return _skipped("no workspace found")

    from pipeline.llm.models_catalog import default_model_for

    model_name = default_model_for("anthropic")
    service = _build_llm_service(api_key, workspace_id, model_name)
    return _execute_drift_check(service, model_name=model_name)


def _skipped(reason: str) -> dict[str, Any]:
    """Skip é ruidoso por design — job nightly mudo esconde drift em produção."""
    _drift_metrics.error(
        f"extract llm drift skipped: {reason}",
        extra={"stage": DRIFT_STAGE},
    )
    return {"skipped": True, "reason": reason}


def _execute_drift_check(
    llm_client: StructuredLLMClient,
    *,
    model_name: str,
    session_factory: Optional[Callable[[], Any]] = None,
) -> dict[str, Any]:
    """Corpo testável do job — client injetado (fake em CI, LLMService no beat)."""
    results = run_extract_llm_drift(llm_client)
    batch_id = persist_drift_results(
        results, model_name=model_name, session_factory=session_factory
    )
    failed = [r for r in results if not r.passed]
    _emit_drift_metrics(results, failed, batch_id=batch_id, model_name=model_name)
    summary = _drift_summary(results, failed, batch_id)
    logger.info("detect_extract_llm_drift: %s", summary)
    return summary


def _drift_summary(
    results: list[FixtureDriftResult], failed: list[FixtureDriftResult], batch_id: str
) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "fixtures": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
    }


def _emit_drift_metrics(
    results: list[FixtureDriftResult],
    failed: list[FixtureDriftResult],
    *,
    batch_id: str,
    model_name: str,
) -> None:
    for result in failed:
        _emit_drift_failure(result, batch_id=batch_id, model_name=model_name)
    _drift_metrics.info(
        "extract llm drift check completed",
        extra={
            "stage": DRIFT_STAGE,
            "fixtures": len(results),
            "failed": len(failed),
            "model_name": model_name,
            "batch_id": batch_id,
        },
    )


def _emit_drift_failure(result: FixtureDriftResult, *, batch_id: str, model_name: str) -> None:
    _drift_metrics.error(
        "extract llm drift detected",
        extra={
            "stage": DRIFT_STAGE,
            "fixture_id": result.fixture_id,
            "failures": list(result.failures),
            "model_name": model_name,
            "batch_id": batch_id,
        },
    )


def _resolve_drift_workspace() -> Optional[str]:
    """Env explícito > workspace mais antigo (dogfood em dev/prod single-owner)."""
    explicit = os.environ.get(_WORKSPACE_ENV, "").strip()
    if explicit:
        return explicit
    from sqlalchemy import select

    from backend.app.core.database import SyncSessionLocal
    from backend.app.models import Workspace

    with SyncSessionLocal() as db:
        return db.execute(
            select(Workspace.id).order_by(Workspace.created_at.asc()).limit(1)
        ).scalar_one_or_none()


def _build_llm_service(api_key: str, workspace_id: str, model_name: str) -> Any:
    """LLMService com hooks ADR-173 — custo do trial cai no cap do workspace."""
    from backend.app.services.llm_budget_service import LLMBudgetService
    from pipeline.llm.litellm_client import LLMConfig, LLMService

    config = LLMConfig(
        provider="anthropic",
        api_key=api_key,
        model_name=model_name,
        max_tokens=4096,
        call_hooks=LLMBudgetService(workspace_id),
    )
    return LLMService(config)
