"""Use case ``list_consumo_pontuais`` (card "Consumo Consciente")."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction._loading import load_filtered_transactions
from backend.app.application.transaction.filters import TransactionFilters
from backend.app.schemas.report import ConsumoPontuaisItem, ConsumoPontuaisResponse
from backend.app.schemas.transactions import TransactionItem
from pipeline.domain.services import InternalTransferDetector

VALID_PERIODS: tuple[str, ...] = ("3m", "6m", "12m", "ytd")
_DEFAULT_THRESHOLD = Decimal("2000")
_TRANSFER_CATEGORIES = frozenset(
    {"transferencia_entre_contas", "transferencia_familiar", "transferencias_internas"}
)


def _period_start(period: str, today: date) -> date:
    if period == "3m":
        return today - timedelta(days=31 * 3)
    if period == "6m":
        return today - timedelta(days=31 * 6)
    if period == "12m":
        return today.replace(year=today.year - 1)
    return today.replace(month=1, day=1)


def _resolve_period_dates(
    period: str,
    today: date | None = None,
    *,
    anchor_date: date | None = None,
) -> tuple[str, str]:
    """Replica ``frontend/src/lib/periodUtils.ts::getPeriodDates`` (anchor_date evita janela vazia em dados antigos · PR #150)."""
    if period not in VALID_PERIODS:
        raise ValueError(f"period inválido: {period!r} — esperado um de {VALID_PERIODS}")
    end = anchor_date or today or datetime.now(timezone.utc).date()
    return _period_start(period, end).isoformat(), end.isoformat()


def _is_pontual(
    tx: TransactionItem,
    *,
    threshold: Decimal,
    detector: InternalTransferDetector,
) -> bool:
    if tx.origem is not None:
        return False
    if abs(tx.valor) < threshold:
        return False
    if tx.categoria in _TRANSFER_CATEGORIES:
        return False
    if detector.is_internal_transfer(tx.descricao or "", banco=tx.banco or ""):
        return False
    return True


def _to_item(tx: TransactionItem) -> ConsumoPontuaisItem:
    return ConsumoPontuaisItem(
        data=tx.data,
        descricao=tx.descricao,
        valor=abs(tx.valor),
        banco=tx.banco,
        categoria=tx.categoria,
        tipo_conta=tx.tipo_conta,
        titular=tx.titular,
        transaction_hash=tx.transaction_hash,
    )


async def _load_window(
    workspace_id: str, *, date_from: str, date_to: str, db: AsyncSession
) -> list[TransactionItem]:
    return await load_filtered_transactions(
        workspace_id,
        TransactionFilters(date_from=date_from, date_to=date_to),
        db=db,
    )


def _filter_and_sort(
    transactions: list[TransactionItem],
    *,
    threshold: Decimal,
    detector: InternalTransferDetector,
) -> list[TransactionItem]:
    pontuais = [t for t in transactions if _is_pontual(t, threshold=threshold, detector=detector)]
    pontuais.sort(key=lambda t: abs(t.valor), reverse=True)
    return pontuais


async def list_consumo_pontuais(
    workspace_id: str,
    *,
    period: str,
    detector: InternalTransferDetector,
    threshold: Decimal = _DEFAULT_THRESHOLD,
    anchor_date: date | None = None,
    db: AsyncSession,
) -> ConsumoPontuaisResponse:
    date_from, date_to = _resolve_period_dates(period, anchor_date=anchor_date)
    transactions = await _load_window(workspace_id, date_from=date_from, date_to=date_to, db=db)
    pontuais = _filter_and_sort(transactions, threshold=threshold, detector=detector)
    return ConsumoPontuaisResponse(
        period=period,
        date_from=date_from,
        date_to=date_to,
        items=[_to_item(t) for t in pontuais],
        total=len(pontuais),
        total_valor=sum((abs(t.valor) for t in pontuais), Decimal("0")),
    )
