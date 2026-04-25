"""Use case ``list_consumo_pontuais`` (card "Consumo Consciente")."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction._loading import load_filtered_transactions
from backend.app.application.transaction.filters import TransactionFilters
from backend.app.core.config import settings
from backend.app.schemas.report import ConsumoPontuaisItem, ConsumoPontuaisResponse
from backend.app.schemas.transactions import TransactionItem
from pipeline.domain.services import InternalTransferConfig, InternalTransferDetector

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


def _resolve_period_dates(period: str, today: date | None = None) -> tuple[str, str]:
    """Replica ``frontend/src/lib/periodUtils.ts::getPeriodDates``."""
    if period not in VALID_PERIODS:
        raise ValueError(f"period inválido: {period!r} — esperado um de {VALID_PERIODS}")
    today = today or datetime.now(timezone.utc).date()
    return _period_start(period, today).isoformat(), today.isoformat()


def _tenant_config_dir(workspace_id: str) -> Path:
    return Path(settings.STORAGE_ROOT) / workspace_id / "config"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_categorization(workspace_id: str) -> dict[str, Any]:
    tenant_dir = _tenant_config_dir(workspace_id)
    global_dir = settings.PIPELINE_ROOT / "config"
    return _read_json(tenant_dir / "categorization.json") or _read_json(
        global_dir / "categorization.json"
    )


def _load_family(workspace_id: str) -> dict[str, Any]:
    tenant_dir = _tenant_config_dir(workspace_id)
    global_dir = settings.PIPELINE_ROOT / "config"
    return _read_json(tenant_dir / "family_members.json") or _read_json(
        global_dir / "family_members.json"
    )


def _merge_transfer_config(
    categorization: dict[str, Any], family: dict[str, Any]
) -> dict[str, Any]:
    transferencias = (family.get("transferencias_internas") or {}) if family else {}
    merged = dict(categorization)
    patterns = list(merged.get("internal_transfer_patterns") or [])
    patterns += list(transferencias.get("patterns_pix") or [])
    merged["internal_transfer_patterns"] = patterns
    merged["internal_transfer_recipients"] = list(transferencias.get("recipients") or [])
    merged["bank_specific_transfer_patterns"] = transferencias.get("patterns_bank_specific") or {}
    merged["global_transfer_patterns"] = list(transferencias.get("patterns_global") or [])
    return merged


def _build_internal_transfer_detector(workspace_id: str) -> InternalTransferDetector:
    """Detector tipado a partir do config materializado no tenant (ou global)."""
    categorization = _load_categorization(workspace_id)
    family = _load_family(workspace_id)
    merged = _merge_transfer_config(categorization, family)
    return InternalTransferDetector(InternalTransferConfig.from_categorization(merged))


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
    threshold: Decimal | None = None,
    db: AsyncSession,
) -> ConsumoPontuaisResponse:
    threshold_value = threshold if threshold is not None else _DEFAULT_THRESHOLD
    date_from, date_to = _resolve_period_dates(period)
    transactions = await _load_window(workspace_id, date_from=date_from, date_to=date_to, db=db)
    detector = _build_internal_transfer_detector(workspace_id)
    pontuais = _filter_and_sort(transactions, threshold=threshold_value, detector=detector)
    return ConsumoPontuaisResponse(
        period=period,
        date_from=date_from,
        date_to=date_to,
        items=[_to_item(t) for t in pontuais],
        total=len(pontuais),
        total_valor=sum((abs(t.valor) for t in pontuais), Decimal("0")),
    )
