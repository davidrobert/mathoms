"""Apply retroativo engine — extraído de ``rule_management_service`` para SRP + P2 baseline (ADR-188 PR3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from backend.app.application.categorization._caps import SYNC_APPLY_THRESHOLD
from backend.app.application.categorization.rule_preview_service import (
    build_synthetic_rules,
    period_from_data,
)
from backend.app.models.categorization_rule import CategorizationRule
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
    OVERRIDE_NATURAL_KEY_V2_FLAG,
    OverrideMatchIndex,
)
from backend.app.services.override_identity import identity_from_transaction_item
from backend.app.services.report_publication import is_month_closed_sync
from backend.app.services.transaction_service import natural_key_for_match
from pipeline.domain.services.categorization_service import normalize_narrative
from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferDetector,
)


class ApplyTooLargeError(Exception):
    """Apply retroativo excede ``SYNC_APPLY_THRESHOLD``. Caller (service) traduz
    para erro de domínio. Local subclass evita ciclo com base.errors."""

    def __init__(self, *, expected_overrides: int) -> None:
        super().__init__(
            f"Apply retroativo síncrono limitado a {SYNC_APPLY_THRESHOLD} overrides; "
            f"esta regra tocaria {expected_overrides}. PR3 implementa async Celery."
        )
        self.expected_overrides = expected_overrides


@dataclass
class _ApplyCtx:
    """Contexto do apply retroativo (R9)."""

    workspace_id: str
    rule: CategorizationRule
    detector: InternalTransferDetector
    db: Session
    closed_cache: dict[str, bool]
    match_index: OverrideMatchIndex


def _hash_scope(matching: list, v2_enabled: bool):
    """Scope SQL por v1 (+v2 sob flag-ON — dual-read ADR-282)."""
    scope = TransactionOverride.transaction_hash.in_([tx.transaction_hash for tx in matching])
    if not v2_enabled:
        return scope
    v2_hashes = [identity_from_transaction_item(tx).natural_key_hash for tx in matching]
    return or_(scope, TransactionOverride.natural_key_hash.in_(v2_hashes))


def _existing_override_index(
    db: Session,
    workspace_id: str,
    *,
    matching: list,
    v2_enabled: bool,
) -> OverrideMatchIndex:
    """Overrides ativos das txs candidatas (sticky check; scope p/ perf, ADR-188 PR3 R2/R3)."""
    if not matching:
        return OverrideMatchIndex(workspace_id=workspace_id, v2_enabled=v2_enabled)
    stmt = (
        select(TransactionOverride)
        .where(
            TransactionOverride.workspace_id == workspace_id,
            TransactionOverride.deleted_at.is_(None),
            _hash_scope(matching, v2_enabled),
        )
        .order_by(TransactionOverride.created_at, TransactionOverride.id)
    )
    rows = db.execute(stmt).scalars().all()
    return OverrideMatchIndex.from_overrides(rows, workspace_id=workspace_id, v2_enabled=v2_enabled)


def _is_existing_sticky(
    existing: Optional[TransactionOverride],  # None quando tx sem override prévio (semântica)
    rule_id: str,
) -> bool:
    """Existing override impede novo rule override (manual ou outra rule)."""
    if existing is None:
        return False
    if existing.source == OVERRIDE_SOURCE_MANUAL:
        return True
    return existing.source == OVERRIDE_SOURCE_RULE and existing.rule_id != rule_id


def _period_is_closed(
    period: Optional[str],  # None se tx.data não puder ser parseado (semântica)
    ctx: _ApplyCtx,
) -> bool:
    if period is None:
        return False
    if period not in ctx.closed_cache:
        ctx.closed_cache[period] = is_month_closed_sync(ctx.workspace_id, period, db=ctx.db)
    return ctx.closed_cache[period]


def _match_existing(tx, ctx: _ApplyCtx) -> Optional[TransactionOverride]:
    """Override ativo da tx — dual-read v2→v1 sob flag-ON (ADR-282)."""
    return ctx.match_index.match(
        natural_key_hash=natural_key_for_match(tx, ctx.match_index),
        legacy_hash=tx.transaction_hash,
    )


def _build_override_values(tx, ctx: _ApplyCtx) -> dict:
    """Valores para INSERT ``transaction_overrides(source='rule')``."""
    values = {
        "id": str(uuid.uuid4()),
        "workspace_id": ctx.workspace_id,
        "transaction_hash": tx.transaction_hash,
        "original_category": tx.categoria,
        "new_category": ctx.rule.target_category,
        "source": OVERRIDE_SOURCE_RULE,
        "rule_id": ctx.rule.id,
        "reviewed": True,
        "created_at": datetime.now(timezone.utc),
        "deleted_at": None,
    }
    # ADR-282 dual-write: hash v2 + snapshot (match segue no transaction_hash
    # legado enquanto a flag está off). Paridade com o learning loop.
    values.update(identity_from_transaction_item(tx).as_columns())
    return values


def _dialect_insert(db: Session):
    """Dialect-aware ``insert(...)`` — copia do learning_loop."""
    dialect_name = db.bind.dialect.name if db.bind else "sqlite"
    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    return dialect_insert


def _upsert_rule_override(values: dict, db: Session) -> None:
    """``INSERT ... ON CONFLICT DO UPDATE`` — paridade learning_loop (ADR-188 §D4)."""
    dialect_insert = _dialect_insert(db)
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
    db.execute(stmt)


def _matching_transactions(rule: CategorizationRule, transactions: list) -> list:
    """Lista de txs que casam keyword da rule — usa ``match_normalized`` (perf R1)."""
    rules = build_synthetic_rules(rule.keyword, rule.target_category)
    return [
        t
        for t in transactions
        if rules.match_normalized(normalize_narrative(t.descricao)) is not None
    ]


def filter_matching(rule: CategorizationRule, transactions: list) -> list:
    """Matching list + threshold guard (sync path)."""
    matching = _matching_transactions(rule, transactions)
    if len(matching) > SYNC_APPLY_THRESHOLD:
        raise ApplyTooLargeError(expected_overrides=len(matching))
    return matching


def count_matching(rule_keyword: str, rule_target: str, transactions: list) -> int:
    """Conta matches sem levantar — usado pelo router p/ decidir sync vs async."""

    class _Proxy:
        pass

    proxy = _Proxy()
    proxy.keyword = rule_keyword
    proxy.target_category = rule_target
    return len(_matching_transactions(proxy, transactions))


def _update_rule_override_in_place(existing: TransactionOverride, tx, ctx: _ApplyCtx) -> None:
    """Existing casado via v2 com v1 drifted não dispara o ON CONFLICT (UK é no
    v1) — update in-place evita duplicata de ``natural_key_hash`` (ADR-282)."""
    existing.rule_id = ctx.rule.id
    existing.new_category = ctx.rule.target_category
    existing.original_category = tx.categoria
    for column, value in identity_from_transaction_item(tx).as_columns().items():
        setattr(existing, column, value)


def _apply_one(tx, ctx: _ApplyCtx) -> bool:
    """``True`` se aplicou; ``False`` se pulou (sticky/mês fechado/transfer)."""
    if ctx.detector.is_internal_transfer(tx.descricao or "", banco=tx.banco or ""):
        return False
    existing = _match_existing(tx, ctx)
    if _is_existing_sticky(existing, ctx.rule.id):
        return False
    if _period_is_closed(period_from_data(tx.data), ctx):
        return False
    if ctx.match_index.v2_enabled and existing is not None:
        _update_rule_override_in_place(existing, tx, ctx)
    else:
        _upsert_rule_override(_build_override_values(tx, ctx), ctx.db)
    return True


def _build_ctx(*, workspace_id: str, rule: CategorizationRule, detector, db, matching):
    v2_enabled = is_enabled_sync(workspace_id, OVERRIDE_NATURAL_KEY_V2_FLAG, db=db)
    return _ApplyCtx(
        workspace_id=workspace_id,
        rule=rule,
        detector=detector,
        db=db,
        closed_cache={},
        match_index=_existing_override_index(
            db, workspace_id, matching=matching, v2_enabled=v2_enabled
        ),
    )


def apply_retroactive_sync(
    *,
    workspace_id: str,
    rule: CategorizationRule,
    detector: InternalTransferDetector,
    transactions: list,
    db: Session,
) -> int:
    """Apply síncrono (≤``SYNC_APPLY_THRESHOLD``). Retorna applied count."""
    matching = filter_matching(rule, transactions)
    ctx = _build_ctx(
        workspace_id=workspace_id,
        rule=rule,
        detector=detector,
        db=db,
        matching=matching,
    )
    applied = sum(1 for tx in matching if _apply_one(tx, ctx))
    if applied > 0:
        CategorizationRuleRepository(db).bump_applied_count(rule_id=rule.id, delta=applied)
    return applied


def apply_retroactive_async_safe(
    *,
    workspace_id: str,
    rule: CategorizationRule,
    detector: InternalTransferDetector,
    transactions: list,
    db: Session,
) -> int:
    """Apply async (Celery) — sem threshold cap, idempotente via COUNT pós-fato."""
    matching = _matching_transactions(rule, transactions)
    ctx = _build_ctx(
        workspace_id=workspace_id,
        rule=rule,
        detector=detector,
        db=db,
        matching=matching,
    )
    for tx in matching:
        _apply_one(tx, ctx)
    return count_applied_overrides(db, workspace_id, rule.id)


def count_applied_overrides(db: Session, workspace_id: str, rule_id: str) -> int:
    """COUNT(*) de overrides ativos da regra — fonte canônica em fluxos async."""
    stmt = select(func.count(TransactionOverride.id)).where(
        TransactionOverride.workspace_id == workspace_id,
        TransactionOverride.rule_id == rule_id,
        TransactionOverride.source == OVERRIDE_SOURCE_RULE,
        TransactionOverride.deleted_at.is_(None),
    )
    return int(db.execute(stmt).scalar_one() or 0)


def set_applied_count(*, rule_id: str, applied: int, db: Session) -> None:
    """Seta ``applied_count`` (não bump) — idempotente em retry Celery."""
    db.execute(
        sa_update(CategorizationRule)
        .where(CategorizationRule.id == rule_id)
        .values(
            applied_count=applied,
            updated_at=datetime.now(timezone.utc),
        )
    )
