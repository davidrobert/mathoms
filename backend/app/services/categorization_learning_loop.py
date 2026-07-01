"""Learning loop pós-E4: aplica ``TransactionOverride(source='rule')`` (ADR-186 §D5 / ADR-188 §D4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

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
from backend.app.services.feature_flags_service import is_enabled_sync
from backend.app.services.override_dual_read import (
    OVERRIDE_DUAL_READ_SHADOW_COMPARE_FLAG,
    OVERRIDE_NATURAL_KEY_V2_FLAG,
    OverrideMatchIndex,
    persist_dualread_snapshot,
)
from backend.app.services.override_identity import identity_from_classified_tx
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


def _preload_override_index(
    db: Session, workspace_id: str, *, v2_enabled: bool, shadow_compare: bool = False
) -> OverrideMatchIndex:
    """Overrides ATIVOS (``deleted_at IS NULL`` · ADR-188 §D1) — dual-read ADR-282."""
    rows = (
        db.execute(
            select(TransactionOverride)
            .where(
                TransactionOverride.workspace_id == workspace_id,
                TransactionOverride.deleted_at.is_(None),
            )
            .order_by(TransactionOverride.created_at, TransactionOverride.id)
        )
        .scalars()
        .all()
    )
    return OverrideMatchIndex.from_overrides(
        rows, workspace_id=workspace_id, v2_enabled=v2_enabled, shadow_compare=shadow_compare
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
    match_index: OverrideMatchIndex
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


def _build_insert_values(
    *, workspace_id: str, tx_hash: str, tx: ClassifiedTransaction
) -> dict[str, Any]:
    """Valores para INSERT ... ON CONFLICT (``orig == new`` por contrato P3)."""
    values = {
        "id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "transaction_hash": tx_hash,
        "original_category": tx.categoria,
        "new_category": tx.categoria,
        "source": OVERRIDE_SOURCE_RULE,
        "rule_id": tx.learned_rule_id,
        "reviewed": True,
        "created_at": datetime.now(timezone.utc),
        "deleted_at": None,
    }
    # ADR-282 dual-write: popula natural_key v2 + snapshot (match segue no
    # transaction_hash legado enquanto a flag está off).
    values.update(identity_from_classified_tx(tx).as_columns())
    return values


def _dialect_insert(db: Session):
    """Dialect-aware ``insert(...)`` — SQLite e Postgres ambos suportam ON CONFLICT."""
    dialect_name = db.bind.dialect.name if db.bind else "sqlite"
    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        # SQLite (≥3.24) supports ON CONFLICT; tests + dev use SQLite.
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    return dialect_insert


def _upsert_via_on_conflict(state: _LoopState, values: dict[str, Any]) -> None:
    """``INSERT ... ON CONFLICT DO UPDATE`` safety net contra race (ADR-188 §D4)."""
    dialect_insert = _dialect_insert(state.db)
    stmt = dialect_insert(TransactionOverride.__table__).values(**values)
    update_set = {
        "rule_id": stmt.excluded.rule_id,
        "new_category": stmt.excluded.new_category,
        "original_category": stmt.excluded.original_category,
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["workspace_id", "transaction_hash"],
        set_=update_set,
        where=TransactionOverride.__table__.c.source == OVERRIDE_SOURCE_RULE,
    )
    state.db.execute(stmt)


def _reflect_in_loop_state(state: _LoopState, values: dict[str, Any]) -> None:
    """Espelha INSERT no ``match_index`` — sticky intra-run (fix #194)."""
    ovr = TransactionOverride(
        id=values["id"],
        workspace_id=values["workspace_id"],
        transaction_hash=values["transaction_hash"],
        original_category=values["original_category"],
        new_category=values["new_category"],
        source=values["source"],
        rule_id=values["rule_id"],
        reviewed=values["reviewed"],
        created_at=values["created_at"],
        deleted_at=None,
        natural_key_hash=values["natural_key_hash"],
        hash_version=values["hash_version"],
    )
    state.match_index.add(ovr)


def _upsert_rule_override(tx, tx_hash: str, existing, state: _LoopState) -> None:
    """Pre-load + skip + ``ON CONFLICT DO UPDATE`` safety net (ADR-188 §D4)."""
    if existing is not None and existing.source == OVERRIDE_SOURCE_RULE:
        if existing.new_category != tx.categoria:
            existing.new_category = tx.categoria
        return
    values = _build_insert_values(workspace_id=state.workspace_id, tx_hash=tx_hash, tx=tx)
    _upsert_via_on_conflict(state, values)
    _reflect_in_loop_state(state, values)


def _natural_key_for(tx: ClassifiedTransaction, state: _LoopState) -> str | None:
    """Hash v2 da linha E4 classificada — ``None`` com flag off (ADR-282)."""
    if not state.match_index.v2_enabled:
        return None
    return identity_from_classified_tx(tx).natural_key_hash


def _process_one(tx: ClassifiedTransaction, state: _LoopState) -> str:
    """``'applied'`` | ``'skipped_sticky'`` | ``'skipped_closed_month'``."""
    tx_hash = _tx_hash(tx)
    existing = state.match_index.match(
        natural_key_hash=_natural_key_for(tx, state), legacy_hash=tx_hash
    )
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
    # Ordem determinística (ADR-188 §5 risk row — evita deadlock em UPDATE
    # CASE WHEN N regras concorrentes).
    for rule_id in sorted(applied_per_rule):
        repo.bump_applied_count(rule_id=rule_id, delta=applied_per_rule[rule_id])
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


def _build_loop_state(workspace_id: str, db: Session) -> _LoopState:
    """Monta o estado da loop lendo as flags de dual-read/shadow-compare (ADR-282)."""
    v2_enabled = is_enabled_sync(workspace_id, OVERRIDE_NATURAL_KEY_V2_FLAG, db=db)
    shadow_compare = is_enabled_sync(workspace_id, OVERRIDE_DUAL_READ_SHADOW_COMPARE_FLAG, db=db)
    return _LoopState(
        workspace_id=workspace_id,
        db=db,
        match_index=_preload_override_index(
            db, workspace_id, v2_enabled=v2_enabled, shadow_compare=shadow_compare
        ),
        closed_months_cache={},
    )


def apply_learning_loop(
    *,
    workspace_id: str,
    classified: Iterable[ClassifiedTransaction],
    db: Session,
) -> LearningLoopStats:
    """Cria ``TransactionOverride(source='rule')`` por match (ADR-186/187/188)."""
    matched = [t for t in classified if t.learned_rule_id is not None]
    if not matched:
        return LearningLoopStats()
    state = _build_loop_state(workspace_id, db)
    counts, applied_per_rule = _run_loop(matched, state)
    _bump_counters_same_flush(db, applied_per_rule)
    persist_dualread_snapshot(db, state.match_index)
    return LearningLoopStats(matches_total=len(matched), **counts)
