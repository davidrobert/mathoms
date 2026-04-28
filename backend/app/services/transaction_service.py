"""Transaction service — loads E4 unified JSON and applies overrides/filters."""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import Any, Optional

from backend.app.schemas.transactions import TransactionItem, TransactionSummary
from backend.app.services.artifact_reader import read_latest_artifact

logger = logging.getLogger(__name__)


def generate_transaction_hash(tx: dict) -> str:
    raw = f"{tx.get('data', '')}|{tx.get('descricao', '')}|{tx.get('valor', '')}|{tx.get('banco', '')}|{tx.get('titular', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _flatten_e4_payload(data: dict | None, tx_type: str) -> list[dict]:
    """Achata a estrutura `{dados: {categoria: [items]}}` do E4 em lista."""
    if not data:
        return []
    dados = data.get("dados", {})
    transactions: list[dict] = []
    for _category_name, items in dados.items():
        if not isinstance(items, list):
            continue
        for item in items:
            item["_tx_type"] = tx_type
            transactions.append(item)
    return transactions


def load_transactions(workspace_id: str, tenant_root: str) -> list[TransactionItem]:
    receitas_payload = read_latest_artifact(
        workspace_id, stage="E4", key="receitas", tenant_root=tenant_root
    )
    despesas_payload = read_latest_artifact(
        workspace_id, stage="E4", key="despesas", tenant_root=tenant_root
    )

    raw_receitas = _flatten_e4_payload(receitas_payload, "receita")
    raw_despesas = _flatten_e4_payload(despesas_payload, "despesa")

    all_raw = raw_receitas + raw_despesas
    occurrence_counter: dict[str, int] = {}
    items: list[TransactionItem] = []
    for tx in all_raw:
        tx_hash = generate_transaction_hash(tx)
        idx = occurrence_counter.get(tx_hash, 0)
        occurrence_counter[tx_hash] = idx + 1
        items.append(
            TransactionItem(
                data=tx.get("data", ""),
                descricao=tx.get("descricao", ""),
                valor=Decimal(str(tx.get("valor", 0))),
                banco=tx.get("banco", ""),
                categoria=tx.get("categoria", ""),
                origem=tx.get("origem"),
                tipo_conta=tx.get("tipo_conta"),
                titular=tx.get("titular"),
                moeda=tx.get("moeda"),
                transaction_hash=tx_hash,
                row_id=f"{tx_hash}:{idx}",
                is_overridden=False,
            )
        )
    return items


def apply_overrides(
    transactions: list[TransactionItem],
    overrides_map: dict[str, Any],
) -> list[TransactionItem]:
    """Apply DB overrides to transaction list, mutating category in-place."""
    result = []
    for tx in transactions:
        if tx.transaction_hash in overrides_map:
            override = overrides_map[tx.transaction_hash]
            tx = tx.model_copy(
                update={
                    "categoria": override.new_category,
                    "is_overridden": True,
                }
            )
        result.append(tx)
    return result


def filter_transactions(
    transactions: list[TransactionItem],
    *,
    member: Optional[str] = None,
    bank: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    value_min: Optional[float] = None,
    value_max: Optional[float] = None,
    search: Optional[str] = None,
) -> list[TransactionItem]:
    filtered = transactions

    if member:
        filtered = [t for t in filtered if t.titular and member.lower() in t.titular.lower()]
    if bank:
        filtered = [t for t in filtered if bank.lower() in t.banco.lower()]
    if category:
        filtered = [t for t in filtered if category.lower() in t.categoria.lower()]
    if date_from:
        filtered = [t for t in filtered if t.data >= date_from]
    if date_to:
        filtered = [t for t in filtered if t.data <= date_to]
    if value_min is not None:
        vmin = Decimal(str(value_min))
        filtered = [t for t in filtered if abs(t.valor) >= vmin]
    if value_max is not None:
        vmax = Decimal(str(value_max))
        filtered = [t for t in filtered if abs(t.valor) <= vmax]
    if search:
        q = search.lower()
        filtered = [t for t in filtered if q in t.descricao.lower() or q in t.categoria.lower()]

    return filtered


def paginate_transactions(
    transactions: list[TransactionItem],
    page: int,
    page_size: int,
) -> tuple[list[TransactionItem], TransactionSummary]:
    sorted_txs = sorted(transactions, key=lambda t: t.data, reverse=True)

    zero = Decimal("0")
    receitas = sum((t.valor for t in sorted_txs if t.origem is not None), zero)
    despesas = sum((t.valor for t in sorted_txs if t.origem is None), zero)
    dates = [t.data for t in sorted_txs if t.data]

    summary = TransactionSummary(
        total_receitas=receitas,
        total_despesas=despesas,
        saldo=receitas - despesas,
        count=len(sorted_txs),
        periodo_inicio=min(dates) if dates else None,
        periodo_fim=max(dates) if dates else None,
    )

    start = (page - 1) * page_size
    end = start + page_size
    page_items = sorted_txs[start:end]

    return page_items, summary
