"""Use case ``list_consumo_pontuais`` (card "Consumo Consciente")."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction._loading import load_filtered_transactions
from backend.app.application.transaction.filters import TransactionFilters
from backend.app.schemas.report import ConsumoPontuaisItem, ConsumoPontuaisResponse
from backend.app.schemas.transactions import TransactionItem
from pipeline.domain.services import GastoPontualPolicy, InternalTransferDetector
from pipeline.domain.services.gasto_pontual_policy import VeredictoPontual

VALID_PERIODS: tuple[str, ...] = ("3m", "6m", "12m", "ytd")

# A40.l98 — o limiar e os conjuntos vinham de literais próprios deste módulo,
# disjuntos dos do KPI do MESMO card. O default aqui só vale quando o caller
# não resolve a policy (nenhum caller de produção); o endpoint a resolve do
# ``scoring.json``, que é a fonte única.
_DEFAULT_POLICY = GastoPontualPolicy()

# [[ADR-425]] §D1 — esta lista é o INVENTÁRIO, não o numerador. O balde
# `nao_identificado` sai do KPI porque é ausência de medição e o parecer ancora
# conselho nele; sai da lista seria o oposto do que a regra quer, porque é aqui
# que a família vê as linhas que só ela pode classificar. A divergência é
# deliberada e vem declarada no card (`base_pontuais.excluidos`).
_VEREDITOS_DO_INVENTARIO = frozenset({VeredictoPontual.incluido, VeredictoPontual.nao_identificado})


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
    policy: GastoPontualPolicy,
    detector: InternalTransferDetector,
) -> bool:
    if tx.origem is not None:
        return False
    if not policy.is_relevante(tx.valor):
        return False
    # A40.l98 — mesmas cláusulas de natureza do KPI do MESMO card. Faltavam duas
    # aqui: `recorrentes` (o aluguel de R$ 5k entrava 12× como "gasto pontual") e
    # `transferencia_patrimonial` (o aporte).
    veredito = policy.classify(
        tx.categoria or "",
        descricao=tx.descricao or "",
        banco=tx.banco or "",
        detector=detector,
    )
    return veredito in _VEREDITOS_DO_INVENTARIO


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
    policy: GastoPontualPolicy,
    detector: InternalTransferDetector,
) -> list[TransactionItem]:
    pontuais = [t for t in transactions if _is_pontual(t, policy=policy, detector=detector)]
    pontuais.sort(key=lambda t: abs(t.valor), reverse=True)
    return pontuais


async def list_consumo_pontuais(
    workspace_id: str,
    *,
    period: str,
    detector: InternalTransferDetector,
    policy: GastoPontualPolicy = _DEFAULT_POLICY,
    anchor_date: date | None = None,
    db: AsyncSession,
) -> ConsumoPontuaisResponse:
    date_from, date_to = _resolve_period_dates(period, anchor_date=anchor_date)
    transactions = await _load_window(workspace_id, date_from=date_from, date_to=date_to, db=db)
    pontuais = _filter_and_sort(transactions, policy=policy, detector=detector)
    return ConsumoPontuaisResponse(
        period=period,
        date_from=date_from,
        date_to=date_to,
        items=[_to_item(t) for t in pontuais],
        total=len(pontuais),
        total_valor=sum((abs(t.valor) for t in pontuais), Decimal("0")),
    )
