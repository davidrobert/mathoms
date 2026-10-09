"""``LLMBudgetService`` — budget hard-stop + ``LLMCallLog`` universal (ADR-173).

Implementação backend do protocol ``pipeline.llm.call_hooks.LLMCallHooks``,
injetada em ``WorkspaceContext.llm_call_hooks`` por ``_setup_run_context``
(Celery) e no ``ParecerOrchestratorConfig`` pelo stage wrapper.

Sessões sync curtas por operação (worker Celery é sync); cache Redis 60s
para ``SUM(cost_usd)`` — falha aberta para o SQL. Burst de até 60s pós-110%
é aceito pela ADR-173.

Em engine de writer único (SQLite) o service de um run do pipeline ADIA o
``LLMCallLog``: a sessão do stage segura o write-lock do 1º ``store.write``
até o commit (ADR-256), e o INSERT de outra conexão esperava o busy_timeout e
se perdia. Quem fecha a sessão do stage chama ``flush_call_log`` (ADR-173
§Emenda 2026-10-08).
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Optional

from sqlalchemy import func, select

from backend.app.core.logging import get_logger
from pipeline.llm.call_hooks import LLMBudgetExceededError, stage_without_document_suffix

if TYPE_CHECKING:
    from pipeline.llm.litellm_client import LLMCallResult

logger = logging.getLogger(__name__)
_budget_metrics = get_logger("llm.budget_warn")
_call_log_failures = get_logger("llm.call_log_persist_failed")

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


@dataclass(frozen=True)
class _CallLogEntry:
    """Row de ``LLMCallLog`` congelada na hora da call — ``id``/``created_at`` não esperam o flush."""

    id: str
    created_at: datetime
    stage: str
    model_name: str
    prompt_version: Optional[str]
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal
    cost_known: bool
    duration_ms: int
    confidence: Optional[float]
    needs_review: bool


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
        # O pendente vive o tempo da instância (o run no Celery, o stage no
        # executor HTTP/CLI), nunca entre requests (STATELESS_AUDIT §2). Lock:
        # o extract_with_llm chama o LLM em ThreadPoolExecutor com este service.
        self._defer_call_log = False
        self._pending: list[_CallLogEntry] = []
        self._pending_lock = threading.Lock()

    @classmethod
    def for_pipeline_run(
        cls,
        workspace_id: str,
        run_id: str,
        *,
        session_factory: Optional[Callable[[], Any]] = None,
    ) -> "LLMBudgetService":
        """Hooks de um run do pipeline: adia o ``LLMCallLog`` quando o engine tem writer único."""
        service = cls(workspace_id, pipeline_run_id=run_id, session_factory=session_factory)
        service._defer_call_log = _has_single_writer(service._session_factory)
        return service

    # ------------------------------------------------------------------
    # LLMCallHooks protocol
    # ------------------------------------------------------------------

    def check_budget(self) -> None:
        budget = self._load_budget()
        if budget is None or budget <= 0:
            return
        spent = self._month_spend_cached() + self._pending_spend()
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
        entry = _call_log_entry(result, stage=stage or "unknown", prompt_version=prompt_version)
        if self._defer_call_log:
            with self._pending_lock:
                self._pending.append(entry)
            return
        self._insert([entry])
        # Invalida o cache de gasto — o próximo check refaz o SUM já com esta call.
        _redis_delete(self._spend_cache_key())

    # ------------------------------------------------------------------
    # Executor — fim da sessão do stage
    # ------------------------------------------------------------------

    def flush_call_log(self) -> None:
        """Grava o ``LLMCallLog`` adiado; o executor chama DEPOIS de fechar a sessão do stage."""
        # Sai do pendente ANTES do commit e volta se falhar: subcontar por um
        # instante (dentro do burst da ADR-173) é melhor que contar em dobro —
        # hard-stop falso aborta um run já pago.
        with self._pending_lock:
            batch, self._pending = self._pending, []
        if not batch:
            return
        try:
            self._insert(batch)
        except Exception as exc:  # noqa: BLE001 — telemetria nunca derruba o run
            with self._pending_lock:
                self._pending[:0] = batch
            self._log_flush_failure(batch, exc)
            return
        _redis_delete(self._spend_cache_key())

    def _emit_budget_metric(self, event: str, spent: Decimal, budget: Decimal) -> None:
        _budget_metrics.warning(
            event,
            extra={
                "workspace_id": self._workspace_id,
                "spent_usd": str(spent),
                "budget_usd": str(budget),
            },
        )

    def _log_flush_failure(self, batch: list[_CallLogEntry], exc: Exception) -> None:
        # Contável e sem PII: a classe do erro, nunca str(exc) — o StatementError
        # carrega os bound parameters (ADR-404). As rows vão como dead-letter
        # para replay idempotente: o id nasceu na call.
        _call_log_failures.error(
            "llm call_log flush failed",
            extra={
                "workspace_id": self._workspace_id,
                "pipeline_run_id": self._pipeline_run_id,
                "rows": len(batch),
                "cost_usd": str(sum((entry.cost_usd for entry in batch), Decimal("0"))),
                "error_class": type(exc).__name__,
                "dead_letter": [_dead_letter(entry) for entry in batch],
            },
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _insert(self, entries: list[_CallLogEntry]) -> None:
        from backend.app.models.llm_call_log import LLMCallLog

        rows = [self._row_values(entry) for entry in entries]
        session = self._session_factory()
        try:
            insert = _idempotent_insert(session.get_bind().dialect.name)
            # ON CONFLICT: re-flush de lote cujo commit aterrissou (ack perdido)
            # vira no-op — o id fixo sozinho abortaria o lote inteiro.
            stmt = insert(LLMCallLog.__table__).on_conflict_do_nothing(index_elements=["id"])
            session.execute(stmt, rows)
            session.commit()
        finally:
            session.close()

    def _row_values(self, entry: _CallLogEntry) -> dict[str, Any]:
        return {
            **asdict(entry),
            "workspace_id": self._workspace_id,
            "pipeline_run_id": self._pipeline_run_id,
        }

    def _pending_spend(self) -> Decimal:
        """Gasto adiado do mês corrente — já foi cobrado, e o hard-stop tem de vê-lo antes do flush."""
        month_start, _ = _current_month_window()
        with self._pending_lock:
            costs = [entry.cost_usd for entry in self._pending if entry.created_at >= month_start]
        return sum(costs, Decimal("0"))

    def _spend_cache_key(self) -> str:
        _, month_key = _current_month_window()
        return spend_cache_key(self._workspace_id, month_key)

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
        key = self._spend_cache_key()
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
# LLMCallLog — row, writer único e dead-letter
# ---------------------------------------------------------------------------


def _call_log_entry(
    result: "LLMCallResult", *, stage: str, prompt_version: Optional[str]
) -> _CallLogEntry:
    return _CallLogEntry(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        stage=stage,
        model_name=result.model,
        prompt_version=prompt_version,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=Decimal(str(result.cost_estimate_usd)),
        cost_known=result.cost_known,
        duration_ms=result.duration_ms,
        **_quality_fields(result),
    )


def _has_single_writer(session_factory: Callable[[], Any]) -> bool:
    # SQLite admite UM writer por arquivo, e a sessão do stage segura o lock do
    # 1º store.write até o commit (ADR-256): o INSERT de outra conexão — outro
    # engine inclusive — espera o busy_timeout e falha. Postgres não tem esse
    # lock e grava na hora; adiar lá só trocaria durabilidade por nada.
    session = session_factory()
    try:
        return session.get_bind().dialect.name == "sqlite"
    finally:
        session.close()


def _idempotent_insert(dialect: str) -> Callable[..., Any]:
    """``insert`` com ``on_conflict_do_nothing`` dos dois dialects que o repo roda."""
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        return pg_insert
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        return sqlite_insert
    raise ValueError(
        f"LLMCallLog sem insert idempotente para dialect={dialect!r} (sqlite|postgresql)"
    )


def _dead_letter(entry: _CallLogEntry) -> dict[str, Any]:
    """Row para replay sem PII: o stage perde o sufixo por documento (A42.l7 itens 1/5)."""
    return {
        "id": entry.id,
        "created_at": entry.created_at.isoformat(),
        "stage": stage_without_document_suffix(entry.stage),
        "model_name": entry.model_name,
        "prompt_version": entry.prompt_version,
        # "usage", não "tokens_*": a denylist de log casa "token" por substring.
        "usage": [entry.tokens_in, entry.tokens_out],
        "cost_usd": str(entry.cost_usd),
        "cost_known": entry.cost_known,
        "duration_ms": entry.duration_ms,
    }


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
