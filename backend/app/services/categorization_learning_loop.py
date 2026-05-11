"""Learning loop pós-E4: aplica ``TransactionOverride(source='rule')`` (ADR-186 §D5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    OVERRIDE_SOURCE_RULE,
    TransactionOverride,
)
from backend.app.repositories.categorization_rule_repository import (
    CategorizationRuleRepository,
)
from backend.app.services.report_publication import is_month_closed_sync
from backend.app.services.transaction_service import generate_transaction_hash
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction


@dataclass(frozen=True)
class LearningLoopStats:
    """Telemetria mínima (ADR-186 §D6 · namespace ``mathoms.categorization.*``)."""

    matches_total: int = 0
    applied: int = 0
    skipped_sticky: int = 0
    skipped_closed_month: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "matches_total": self.matches_total,
            "applied": self.applied,
            "skipped_sticky": self.skipped_sticky,
            "skipped_closed_month": self.skipped_closed_month,
        }


def _period_from_data(data_str: str) -> str | None:
    """YYYYMM extraído de ISO ``YYYY-MM-DD``."""
    if not data_str or len(data_str) < 7:
        return None
    yyyy, mm = data_str[:4], data_str[5:7]
    if not (yyyy.isdigit() and mm.isdigit()):
        return None
    return f"{yyyy}{mm}"


def _tx_hash(tx: ClassifiedTransaction) -> str:
    return generate_transaction_hash(
        {
            "data": tx.data,
            "descricao": tx.descricao,
            "valor": tx.valor,
            "banco": tx.banco,
            "titular": tx.titular,
        }
    )


def _preload_overrides(db: Session, workspace_id: str) -> dict[str, TransactionOverride]:
    """Pre-carrega todos overrides do workspace — protege sticky-manual + idempotência."""
    rows = (
        db.execute(
            select(TransactionOverride).where(
                TransactionOverride.workspace_id == workspace_id,
            )
        )
        .scalars()
        .all()
    )
    return {ovr.transaction_hash: ovr for ovr in rows}


def _make_rule_override(
    *, workspace_id: str, tx_hash: str, tx: ClassifiedTransaction
) -> TransactionOverride:
    """``original_category`` = ``new_category`` (P3 revert hard-deleta a linha)."""
    return TransactionOverride(
        workspace_id=workspace_id,
        transaction_hash=tx_hash,
        original_category=tx.categoria,
        new_category=tx.categoria,
        source=OVERRIDE_SOURCE_RULE,
        rule_id=tx.learned_rule_id,
    )


def _is_month_closed_cached(
    workspace_id: str, period: str, cache: dict[str, bool], db: Session
) -> bool:
    if period not in cache:
        cache[period] = is_month_closed_sync(workspace_id, period, db=db)
    return cache[period]


@dataclass
class _LoopState:
    """Estado mutável da loop (R9: agrupar parâmetros longos)."""

    workspace_id: str
    db: Session
    existing_by_hash: dict[str, TransactionOverride]
    closed_months_cache: dict[str, bool]


def _is_sticky(existing, tx) -> bool:
    # sticky intra-run: regra anterior na run casou esta txn — 1ª regra (sort) vence.
    if existing is None:
        return False
    if existing.source == OVERRIDE_SOURCE_MANUAL:
        return True
    return existing.source == OVERRIDE_SOURCE_RULE and existing.rule_id != tx.learned_rule_id


def _check_skip(tx, existing, state: _LoopState) -> str | None:
    """``'skipped_sticky'`` | ``'skipped_closed_month'`` | None."""
    if _is_sticky(existing, tx):
        return "skipped_sticky"
    period = _period_from_data(tx.data)
    if period and _is_month_closed_cached(
        state.workspace_id, period, state.closed_months_cache, state.db
    ):
        return "skipped_closed_month"
    return None


def _upsert_rule_override(tx, tx_hash: str, existing, state: _LoopState) -> None:
    """Idempotente: update se ``source='rule'`` (mesma regra) já existe, senão INSERT."""
    if existing is not None and existing.source == OVERRIDE_SOURCE_RULE:
        if existing.new_category != tx.categoria:
            existing.new_category = tx.categoria
        return
    ovr = _make_rule_override(workspace_id=state.workspace_id, tx_hash=tx_hash, tx=tx)
    state.db.add(ovr)
    state.existing_by_hash[tx_hash] = ovr


def _process_one(tx: ClassifiedTransaction, state: _LoopState) -> str:
    """``'applied'`` | ``'skipped_sticky'`` | ``'skipped_closed_month'``."""
    tx_hash = _tx_hash(tx)
    existing = state.existing_by_hash.get(tx_hash)
    skip = _check_skip(tx, existing, state)
    if skip is not None:
        return skip
    _upsert_rule_override(tx, tx_hash, existing, state)
    return "applied"


def _bump_counters_same_flush(db: Session, applied_per_rule: dict[str, int]) -> None:
    """Bump ``applied_count`` em batch + único flush (ressalva data-eng)."""
    if not applied_per_rule:
        return
    repo = CategorizationRuleRepository(db)
    for rule_id, delta in applied_per_rule.items():
        repo.bump_applied_count(rule_id=rule_id, delta=delta)
    db.flush()


def _run_loop(matched: list[ClassifiedTransaction], state: _LoopState) -> tuple[dict, dict]:
    """Retorna ``(counts, applied_per_rule)``."""
    counts = {"applied": 0, "skipped_sticky": 0, "skipped_closed_month": 0}
    applied_per_rule: dict[str, int] = {}
    for tx in matched:
        outcome = _process_one(tx, state)
        counts[outcome] += 1
        if outcome == "applied":
            applied_per_rule[tx.learned_rule_id] = applied_per_rule.get(tx.learned_rule_id, 0) + 1
    return counts, applied_per_rule


def apply_learning_loop(
    *,
    workspace_id: str,
    classified: Iterable[ClassifiedTransaction],
    db: Session,
) -> LearningLoopStats:
    """Cria ``TransactionOverride(source='rule')`` por match (ADR-186/187)."""
    matched = [t for t in classified if t.learned_rule_id is not None]
    if not matched:
        return LearningLoopStats()
    state = _LoopState(
        workspace_id=workspace_id,
        db=db,
        existing_by_hash=_preload_overrides(db, workspace_id),
        closed_months_cache={},
    )
    counts, applied_per_rule = _run_loop(matched, state)
    _bump_counters_same_flush(db, applied_per_rule)
    return LearningLoopStats(matches_total=len(matched), **counts)
