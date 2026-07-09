"""Transaction service — loads E4 unified JSON and applies overrides/filters."""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import Any, Optional

from backend.app.schemas.transactions import TransactionItem, TransactionSummary
from backend.app.services.override_dual_read import OverrideMatchIndex
from backend.app.services.override_identity import identity_from_transaction_item
from backend.app.services.storage.artifact_reader import read_latest_artifact
from pipeline.stage_spec import resolve_stage_name

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


def _item_from_raw(tx: dict) -> TransactionItem:
    """Linha E4 crua → ``TransactionItem`` sem ``row_id`` (atribuído no loader)."""
    return TransactionItem(
        data=tx.get("data", ""),
        descricao=tx.get("descricao", ""),
        valor=Decimal(str(tx.get("valor", 0))),
        banco=tx.get("banco", ""),
        categoria=tx.get("categoria", ""),
        origem=tx.get("origem"),
        tipo_conta=tx.get("tipo_conta"),
        titular=tx.get("titular"),
        moeda=tx.get("moeda"),
        # ADR-282: bucket E4 carrega a direction de domínio que o ``abs``
        # da despesa destrói no payload — ``credito`` p/ receita, ``debito``
        # p/ despesa. Único sinal autoritativo de tipo no read-path.
        tipo="credito" if tx.get("_tx_type") == "receita" else "debito",
        transaction_hash=generate_transaction_hash(tx),
        row_id="",
        is_overridden=False,
    )


def load_transactions(workspace_id: str, tenant_root: str) -> list[TransactionItem]:
    _stage = resolve_stage_name("categorize_transactions")
    receitas_payload = read_latest_artifact(
        workspace_id, stage=_stage, key="receitas", tenant_root=tenant_root
    )
    despesas_payload = read_latest_artifact(
        workspace_id, stage=_stage, key="despesas", tenant_root=tenant_root
    )

    raw_receitas = _flatten_e4_payload(receitas_payload, "receita")
    raw_despesas = _flatten_e4_payload(despesas_payload, "despesa")

    all_raw = raw_receitas + raw_despesas
    occurrence_counter: dict[str, int] = {}
    items: list[TransactionItem] = []
    for tx in all_raw:
        item = _item_from_raw(tx)
        # Pré-trabalho Fase E (ADR-282): o row_id opaco do FE deriva da identidade
        # v2 — sobrevive ao drop de transaction_hash (v1), que segue no wire só
        # p/ o match legado do dual-read até a M2.
        row_key = identity_from_transaction_item(item).natural_key_hash
        idx = occurrence_counter.get(row_key, 0)
        occurrence_counter[row_key] = idx + 1
        items.append(item.model_copy(update={"row_id": f"{row_key}:{idx}"}))
    return items


def _apply_one_override(tx: TransactionItem, override: Any) -> TransactionItem:
    return tx.model_copy(
        update={
            "categoria": override.new_category,
            "is_overridden": True,
            "override_source": getattr(override, "source", "manual"),
        }
    )


def natural_key_for_match(tx: TransactionItem, index: OverrideMatchIndex) -> Optional[str]:
    """Hash v2 da linha E4 para o dual-read — ``None`` com flag off (ADR-282)."""
    if not index.v2_enabled:
        return None
    return identity_from_transaction_item(tx).natural_key_hash


def apply_overrides(
    transactions: list[TransactionItem],
    match_index: OverrideMatchIndex,
) -> list[TransactionItem]:
    """Aplica overrides via dual-read v2→v1 (ADR-282; A12 P4 propaga ``source``)."""
    result: list[TransactionItem] = []
    for tx in transactions:
        override = match_index.match(
            natural_key_hash=natural_key_for_match(tx, match_index),
            legacy_hash=tx.transaction_hash,
        )
        result.append(tx if override is None else _apply_one_override(tx, override))
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


def _sort_key_for(sort: str):
    """``valor_desc`` ordena por impacto (A28.l5 — fila de reclassificação)."""
    if sort == "valor_desc":
        return lambda t: (abs(t.valor), t.data)
    return lambda t: t.data


def paginate_transactions(
    transactions: list[TransactionItem],
    page: int,
    page_size: int,
    *,
    sort: str = "data_desc",
) -> tuple[list[TransactionItem], TransactionSummary]:
    sorted_txs = sorted(transactions, key=_sort_key_for(sort), reverse=True)

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
