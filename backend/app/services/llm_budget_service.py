"""``LLMBudgetService`` — budget hard-stop + ``LLMCallLog`` universal (ADR-173).

Implementação backend do protocol ``pipeline.llm.call_hooks.LLMCallHooks``,
injetada em ``WorkspaceContext.llm_call_hooks`` por ``_setup_run_context``
(Celery) e no ``ParecerOrchestratorConfig`` pelo stage wrapper.

Sessões sync curtas por operação (worker Celery é sync); cache Redis 60s
para ``SUM(cost_usd)`` — falha aberta para o SQL. Burst de até 60s pós-110%
é aceito pela ADR-173.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Optional

from sqlalchemy import func, select

from backend.app.core.logging import get_logger
from pipeline.llm.call_hooks import LLMBudgetExceededError

if TYPE_CHECKING:
    from pipeline.llm.litellm_client import LLMCallResult

logger = logging.getLogger(__name__)
_budget_metrics = get_logger("llm.budget_warn")

_SPEND_CACHE_TTL_SECONDS = 60
_WARN_RATIO = Decimal("0.80")
_HARD_STOP_RATIO = Decimal("1.10")

# Contrato público p/ consumidores que precisam de paridade com o hard-stop
# (editor de budget do console interno, A30.l1) — mesmos ratios e janela.
WARN_RATIO = _WARN_RATIO
HARD_STOP_RATIO = _HARD_STOP_RATIO


def spend_cache_key(workspace_id: str, month_key: str) -> str:
    return f"llm_spend:ws={workspace_id}:m={month_key}"


def _current_month_window(now: Optional[datetime] = None) -> tuple[datetime, str]:
    """Início do mês calendário UTC + chave ``YYYYMM`` para o cache."""
    ref = now or datetime.now(timezone.utc)
    start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, f"{ref.year:04d}{ref.month:02d}"


current_month_window = _current_month_window


class LLMBudgetService:
    """Pre-call budget check (80% warn / 110% hard-stop) + persistência por call."""

    def __init__(
        self,
        workspace_id: str,
        *,
        pipeline_run_id: Optional[str] = None,
        session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._pipeline_run_id = pipeline_run_id
        if session_factory is None:
            from backend.app.core.database import SyncSessionLocal

            session_factory = SyncSessionLocal
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # LLMCallHooks protocol
    # ------------------------------------------------------------------

    def check_budget(self) -> None:
        budget = self._load_budget()
        if budget is None or budget <= 0:
            return
        spent = self._month_spend_cached()
        if spent >= budget * _HARD_STOP_RATIO:
            self._emit_budget_metric("llm budget hard-stop", spent, budget)
            raise LLMBudgetExceededError(self._workspace_id, spent, budget)
        if spent >= budget * _WARN_RATIO:
            self._emit_budget_metric("llm budget warn", spent, budget)

    def record_call(
        self,
        result: "LLMCallResult",
        *,
        stage: Optional[str],
        prompt_version: Optional[str],
    ) -> None:
        session = self._session_factory()
        try:
            session.add(self._call_log_row(result, stage, prompt_version))
            session.commit()
        finally:
            session.close()
        # Invalida o cache de gasto — o próximo check refaz o SUM já com esta call.
        _, month_key = _current_month_window()
        _redis_delete(spend_cache_key(self._workspace_id, month_key))

    def _emit_budget_metric(self, event: str, spent: Decimal, budget: Decimal) -> None:
        _budget_metrics.warning(
            event,
            extra={
                "workspace_id": self._workspace_id,
                "spent_usd": str(spent),
                "budget_usd": str(budget),
            },
        )

    def _call_log_row(self, result: "LLMCallResult", stage, prompt_version):
        from backend.app.models.llm_call_log import LLMCallLog

        return LLMCallLog(
            workspace_id=self._workspace_id,
            stage=stage or "unknown",
            model_name=result.model,
            prompt_version=prompt_version,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=Decimal(str(result.cost_estimate_usd)),
            cost_known=result.cost_known,
            duration_ms=result.duration_ms,
            pipeline_run_id=self._pipeline_run_id,
            **_quality_fields(result),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_budget(self) -> Optional[Decimal]:
        """``monthly_llm_budget_usd`` do workspace; ``None`` (NULL/ausente) = sem cap."""
        from backend.app.models import Workspace

        session = self._session_factory()
        try:
            value = session.execute(
                select(Workspace.monthly_llm_budget_usd).where(Workspace.id == self._workspace_id)
            ).scalar_one_or_none()
        finally:
            session.close()
        return None if value is None else Decimal(value)

    def _month_spend_cached(self) -> Decimal:
        _, month_key = _current_month_window()
        key = spend_cache_key(self._workspace_id, month_key)
        cached = _redis_get(key)
        if cached is not None:
            if isinstance(cached, bytes):
                cached = cached.decode("utf-8", errors="replace")
            try:
                return Decimal(cached)
            except (ArithmeticError, TypeError, ValueError):
                logger.warning("llm spend cache parse failed for %s", key)
        spent = self._month_spend_from_db()
        _redis_set(key, str(spent), _SPEND_CACHE_TTL_SECONDS)
        return spent

    def _month_spend_from_db(self) -> Decimal:
        from backend.app.models.llm_call_log import LLMCallLog

        month_start, _ = _current_month_window()
        session = self._session_factory()
        try:
            total = session.execute(
                select(func.coalesce(func.sum(LLMCallLog.cost_usd), 0)).where(
                    LLMCallLog.workspace_id == self._workspace_id,
                    LLMCallLog.created_at >= month_start,
                )
            ).scalar_one()
        finally:
            session.close()
        return Decimal(total or 0)


# ---------------------------------------------------------------------------
# Redis primitives — falha aberta (mesmo padrão de category_cache)
# ---------------------------------------------------------------------------


def _redis_get(key: str) -> Optional[str]:
    client = _get_redis_safe()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception as exc:
        logger.warning("redis GET failed for %s: %s", key, exc)
        return None


def _redis_set(key: str, value: str, ttl_seconds: int) -> None:
    client = _get_redis_safe()
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl_seconds)
    except Exception as exc:
        logger.warning("redis SET failed for %s: %s", key, exc)


def _redis_delete(key: str) -> None:
    client = _get_redis_safe()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:
        logger.warning("redis DEL failed for %s: %s", key, exc)


def _get_redis_safe() -> Any:
    try:
        from backend.app.services.pipeline.events import _get_redis

        return _get_redis()
    except Exception:
        return None


def _quality_fields(result) -> dict:
    """ADR-260 (A20.l12): confidence/needs_review quando o output declara; demais NULL."""
    output = getattr(result, "output", None)
    confidence = getattr(output, "confidence", None)
    return {
        "confidence": float(confidence) if confidence is not None else None,
        "needs_review": bool(getattr(output, "needs_review", False)),
    }
