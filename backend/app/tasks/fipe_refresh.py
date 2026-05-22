"""Celery task `refresh_fipe_value` — ADR-239 D5 (A18 L3 P1+P2)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.market_rate import MarketRate
from backend.app.models.vehicle import Vehicle
from backend.app.services.fipe_lookup import (
    BrasilAPIFipeClient,
    FipeLookupClient,
    FipeLookupError,
    FipeQuote,
)
from backend.app.worker import celery_app

logger = logging.getLogger("mathoms.fipe.refresh")

# Cache TTL: 30 dias após reference_month (ADR-239 D5).
_CACHE_TTL_DAYS = 30


def _fipe_pair(fipe_code: str) -> str:
    """MarketRate.pair = 'fipe_<code>' — schema único compartilhado com câmbio."""
    return f"fipe_{fipe_code}"


def _cache_lookup(db: Session, fipe_code: str, today: date) -> Optional[MarketRate]:
    """Busca cache hit (mais recente, mas dentro do TTL)."""
    row = db.execute(
        select(MarketRate)
        .where(MarketRate.pair == _fipe_pair(fipe_code))
        .order_by(MarketRate.observed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    age_days = (today - row.observed_at).days
    if age_days > _CACHE_TTL_DAYS:
        return None
    return row


def _persist_quote(db: Session, quote: FipeQuote, today: date) -> MarketRate:
    """Materializa quote em MarketRate (idempotente por UNIQUE pair+observed_at)."""
    row = MarketRate(
        pair=_fipe_pair(quote.fipe_code),
        rate=quote.value_brl,
        observed_at=today,
        reference_month=quote.reference_month,
        source=quote.source,
    )
    db.add(row)
    db.flush()
    return row


def refresh_fipe_value_sync(
    fipe_code: str,
    ano_modelo: int,
    *,
    client: Optional[FipeLookupClient] = None,
    db: Optional[Session] = None,
) -> dict:
    """Versão síncrona injetável (testes). Celery task delega para esta."""
    today = date.today()
    if db is not None:
        return _run_with_db(fipe_code, ano_modelo, client or BrasilAPIFipeClient(), db, today)
    with SyncSessionLocal() as session:
        result = _run_with_db(
            fipe_code, ano_modelo, client or BrasilAPIFipeClient(), session, today
        )
        session.commit()
        return result


def _run_with_db(
    fipe_code: str,
    ano_modelo: int,
    client: FipeLookupClient,
    db: Session,
    today: date,
) -> dict:
    """Core orquestrado: cache hit → return; miss → HTTP → persist."""
    cached = _cache_lookup(db, fipe_code, today)
    if cached is not None:
        return _outcome_cache_hit(cached)
    fetched = client.fetch(fipe_code, ano_modelo)
    if isinstance(fetched, FipeLookupError):
        return _outcome_error(fetched)
    row = _persist_quote(db, fetched, today)
    return _outcome_persisted(row, fetched)


def _outcome_cache_hit(row: MarketRate) -> dict:
    return {
        "fipe_code": row.pair.replace("fipe_", ""),
        "status": "fresh",
        "source": "cache",
        "value_brl": str(row.rate),
        "reference_month": row.reference_month or "",
    }


def _outcome_persisted(row: MarketRate, quote: FipeQuote) -> dict:
    return {
        "fipe_code": quote.fipe_code,
        "status": "fresh",
        "source": quote.source,
        "value_brl": str(quote.value_brl),
        "reference_month": quote.reference_month,
    }


def _outcome_error(err: FipeLookupError) -> dict:
    logger.info(
        "mathoms.fipe.refresh_failed",
        extra={
            "fipe_code_prefix": err.fipe_code[:4],
            "status": err.status,
            "reason": err.reason[:120],
        },
    )
    return {
        "fipe_code": err.fipe_code,
        "status": err.status,
        "source": "error",
        "reason": err.reason,
    }


@celery_app.task(name="fin.fipe.refresh", bind=True, max_retries=3, default_retry_delay=120)
def refresh_fipe_value(self, fipe_code: str, ano_modelo: int) -> dict:
    """ADR-239 D5: Celery task — lookup BrasilAPI ass\xc3\xadncrono."""
    try:
        return refresh_fipe_value_sync(fipe_code, ano_modelo)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "mathoms.fipe.refresh_exception",
            extra={"fipe_code_prefix": fipe_code[:4], "reason": str(exc)[:120]},
        )
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


def _retry_countdown(retries: int) -> int:
    """Backoff exponencial: 120s, 240s, 480s (max_retries=3)."""
    return 120 * (2 ** min(retries, 3))


# ===========================================================================
# Batch annual refresh (Celery Beat cron Janeiro — ADR-239 D5)
# ===========================================================================


def _enumerate_active_fipe_codes(db: Session) -> list[tuple[str, int]]:
    """Lista distintos (fipe_code, ano_modelo) de vehicles ativos no workspace global."""
    rows = db.execute(
        select(Vehicle.fipe_code, Vehicle.ano_modelo)
        .where(Vehicle.archived_at.is_(None))
        .where(Vehicle.fipe_code.is_not(None))
        .distinct()
    ).all()
    return [(code, ano) for code, ano in rows if code]


def _enqueue_refresh_async(fipe_code: str, ano_modelo: int) -> None:
    """Enfileira via Celery — separado para test injetar fake."""
    refresh_fipe_value.delay(fipe_code, ano_modelo)


def refresh_all_fipe_values_sync(
    *,
    db: Optional[Session] = None,
    enqueue_fn=_enqueue_refresh_async,
) -> dict:
    """Enumera vehicles ativos + enfileira refresh_fipe_value (síncrono injetável)."""
    if db is None:
        with SyncSessionLocal() as session:
            return _refresh_all_with_db(session, enqueue_fn)
    return _refresh_all_with_db(db, enqueue_fn)


def _refresh_all_with_db(db: Session, enqueue_fn) -> dict:
    codes = _enumerate_active_fipe_codes(db)
    for fipe_code, ano_modelo in codes:
        enqueue_fn(fipe_code, ano_modelo)
    logger.info(
        "mathoms.fipe.refresh_all_enqueued",
        extra={"fipe_codes_count": len(codes)},
    )
    return {"enqueued": len(codes), "fipe_codes": [c for c, _ in codes]}


@celery_app.task(name="fin.fipe.refresh_all_annual", bind=True, max_retries=1)
def refresh_all_fipe_values_annual(self) -> dict:
    """ADR-239 D5: cron Janeiro — refresh anual de todos fipe_codes ativos."""
    return refresh_all_fipe_values_sync()


# ===========================================================================
# Cache reader (consumido pelo ProtecaoAnalyzer runner em A19)
# ===========================================================================


def read_fipe_cache(
    db: Session, fipe_code: str, today: Optional[date] = None
) -> tuple[Optional[Decimal], str]:
    """Retorna `(value_brl, status)` lendo cache market_rates; status=fresh|stale_acceptable|pending_refresh."""
    today = today or date.today()
    row = db.execute(
        select(MarketRate)
        .where(MarketRate.pair == _fipe_pair(fipe_code))
        .order_by(MarketRate.observed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None, "pending_refresh"
    age_days = (today - row.observed_at).days
    return row.rate, "fresh" if age_days <= _CACHE_TTL_DAYS else "stale_acceptable"
