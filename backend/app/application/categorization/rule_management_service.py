"""CRUD ``CategorizationRule`` + apply retroativo (ADR-186/188 · A12 P3 PR2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.application.categorization._caps import (
    RULE_HARD_CAP,
    RULE_SOFT_CAP,
    SYNC_APPLY_THRESHOLD,
)
from backend.app.application.categorization.mappers import rule_to_response
from backend.app.application.categorization.rule_preview_service import (
    build_synthetic_rules,
    period_from_data,
)
from backend.app.core.logging import get_logger
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    OVERRIDE_SOURCE_RULE,
    TransactionOverride,
)
from backend.app.models.workspace import Workspace
from backend.app.repositories.categorization_rule_repository import (
    CategorizationRuleRepository,
)
from backend.app.schemas.dto.categorization_rule import (
    CategorizationRuleResponse,
    RulesListMeta,
    RulesListResponse,
    WarningEntry,
)
from backend.app.services.report_publication import is_month_closed_sync
from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferDetector,
)

logger = get_logger("categorization.rule_mgmt")


# =============================================================================
# Erros tipados específicos (sob DomainError) — handlers em main.py mapeiam
# `code` → mensagem rica.
# =============================================================================


class HardCapExceededError(ValidationError):
    """Workspace atingiu ``rule_cap_override OR RULE_HARD_CAP``. Router → 422."""

    def __init__(self, *, current: int, limit: int) -> None:
        super().__init__(
            f"Hard cap atingido: {current}/{limit} regras ativas. "
            f"Delete regras antigas ou solicite cap_override.",
            code="hard_cap_exceeded",
        )
        self.current = current
        self.limit = limit


class RuleAlreadyExistsError(ConflictError):
    """Já existe regra ativa com mesma (workspace, keyword, target). Router → 409."""

    def __init__(self, *, existing_rule_id: str) -> None:
        super().__init__(
            f"Regra já existe com mesma keyword/categoria (id={existing_rule_id}).",
            code="rule_already_exists",
        )
        self.existing_rule_id = existing_rule_id


class ApplyTooLargeError(ValidationError):
    """Apply retroativo excede ``SYNC_APPLY_THRESHOLD`` — pendente PR3 async. Router → 422."""

    def __init__(self, *, expected_overrides: int) -> None:
        super().__init__(
            f"Apply retroativo síncrono limitado a {SYNC_APPLY_THRESHOLD} overrides; "
            f"esta regra tocaria {expected_overrides}. PR3 implementa async Celery.",
            code="apply_too_large_for_sync",
        )
        self.expected_overrides = expected_overrides


# =============================================================================
# CRUD
# =============================================================================


def _hard_cap_for(workspace: Workspace) -> int:
    return workspace.rule_cap_override or RULE_HARD_CAP


def _count_active_rules(db: Session, workspace_id: str) -> int:
    """Conta regras ativas (``deleted_at IS NULL``)."""
    stmt = select(func.count(CategorizationRule.id)).where(
        CategorizationRule.workspace_id == workspace_id,
        CategorizationRule.deleted_at.is_(None),
    )
    return int(db.execute(stmt).scalar_one() or 0)


def _find_existing_rule(
    db: Session, workspace_id: str, keyword: str, target_category: str
) -> Optional[CategorizationRule]:
    """Procura regra ATIVA com a tripla idêntica (partial unique B-side)."""
    stmt = select(CategorizationRule).where(
        CategorizationRule.workspace_id == workspace_id,
        CategorizationRule.keyword == keyword,
        CategorizationRule.target_category == target_category,
        CategorizationRule.deleted_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


def _existing_overrides_by_hash(db: Session, workspace_id: str) -> dict[str, TransactionOverride]:
    """Overrides ativos por transaction_hash (sticky check)."""
    rows = (
        db.execute(
            select(TransactionOverride).where(
                TransactionOverride.workspace_id == workspace_id,
                TransactionOverride.deleted_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    return {ovr.transaction_hash: ovr for ovr in rows}


@dataclass
class _ApplyCtx:
    """Contexto do apply retroativo (R9)."""

    workspace_id: str
    rule: CategorizationRule
    detector: InternalTransferDetector
    db: Session
    closed_cache: dict[str, bool]
    existing_by_hash: dict[str, TransactionOverride]


def _is_existing_sticky(
    existing: Optional[TransactionOverride],  # None quando tx sem override prévio
    rule_id: str,
) -> bool:
    """Existing override impede novo rule override (manual ou outra rule)."""
    if existing is None:
        return False
    if existing.source == OVERRIDE_SOURCE_MANUAL:
        return True
    return existing.source == OVERRIDE_SOURCE_RULE and existing.rule_id != rule_id


def _period_is_closed(
    period: Optional[str],  # None se tx.data não puder ser parseado
    ctx: _ApplyCtx,
) -> bool:
    if period is None:
        return False
    if period not in ctx.closed_cache:
        ctx.closed_cache[period] = is_month_closed_sync(ctx.workspace_id, period, db=ctx.db)
    return ctx.closed_cache[period]


def _should_skip_for_apply(tx, ctx: _ApplyCtx) -> bool:
    """Pula tx se: mês fechado, manual override, internal transfer, ou já tem rule override."""
    if ctx.detector.is_internal_transfer(tx.descricao or "", banco=tx.banco or ""):
        return True
    if _is_existing_sticky(ctx.existing_by_hash.get(tx.transaction_hash), ctx.rule.id):
        return True
    return _period_is_closed(period_from_data(tx.data), ctx)


def _build_override_values(tx, ctx: _ApplyCtx) -> dict:
    """Valores para INSERT ``transaction_overrides(source='rule')`` — paridade learning_loop."""
    return {
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


def _filter_matching(rule: CategorizationRule, transactions: list) -> list:
    """Aplica o builder sintético em massa; >threshold levanta erro tipado."""
    rules = build_synthetic_rules(rule.keyword, rule.target_category)
    matching = [t for t in transactions if rules.match(t.descricao) is not None]
    if len(matching) > SYNC_APPLY_THRESHOLD:
        raise ApplyTooLargeError(expected_overrides=len(matching))
    return matching


def _apply_one(tx, ctx: _ApplyCtx) -> bool:
    """``True`` se aplicou; ``False`` se pulou (sticky/mês fechado/transfer)."""
    if _should_skip_for_apply(tx, ctx):
        return False
    _upsert_rule_override(_build_override_values(tx, ctx), ctx.db)
    return True


def _apply_retroactive(
    *,
    workspace: Workspace,
    rule: CategorizationRule,
    detector: InternalTransferDetector,
    transactions: list,
    db: Session,
) -> int:
    """Apply em massa — paridade learning_loop. Retorna applied_count."""
    matching = _filter_matching(rule, transactions)
    ctx = _ApplyCtx(
        workspace_id=workspace.id,
        rule=rule,
        detector=detector,
        db=db,
        closed_cache={},
        existing_by_hash=_existing_overrides_by_hash(db, workspace.id),
    )
    applied = sum(1 for tx in matching if _apply_one(tx, ctx))
    if applied > 0:
        CategorizationRuleRepository(db).bump_applied_count(rule_id=rule.id, delta=applied)
    return applied


# =============================================================================
# Public API
# =============================================================================


def _guard_create_preconditions(
    workspace: Workspace, keyword: str, target_category: str, db: Session
) -> None:
    """Cap + conflito exato. Levanta erros tipados ou retorna None."""
    current = _count_active_rules(db, workspace.id)
    limit = _hard_cap_for(workspace)
    if current >= limit:
        raise HardCapExceededError(current=current, limit=limit)
    existing = _find_existing_rule(db, workspace.id, keyword, target_category)
    if existing is not None:
        raise RuleAlreadyExistsError(existing_rule_id=existing.id)


def _make_rule(
    *, workspace_id: str, keyword: str, target_category: str, priority: int, user_id: Optional[str]
) -> CategorizationRule:
    now = datetime.now(timezone.utc)
    return CategorizationRule(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        keyword=keyword,
        target_category=target_category,
        priority=priority,
        enabled=True,
        created_by_user_id=user_id,
        applied_count=0,
        revert_count_manual_edit=0,
        revert_count_rule_disabled=0,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _log_rule_created(rule: CategorizationRule, *, applied: int, user_id: Optional[str]) -> None:
    logger.info(
        "categorization rule created",
        extra={
            "workspace_id": rule.workspace_id,
            "rule_id": rule.id,
            "keyword": rule.keyword,
            "target_category": rule.target_category,
            "applied_retroactive": applied,
            "user_id": user_id,
        },
    )


def create_rule(
    *,
    workspace: Workspace,
    keyword: str,
    target_category: str,
    priority: int,
    user_id: Optional[str],
    detector: InternalTransferDetector,
    transactions: list,
    db: Session,
) -> CategorizationRuleResponse:
    """Cria regra + apply retroativo sync (≤``SYNC_APPLY_THRESHOLD``)."""
    _guard_create_preconditions(workspace, keyword, target_category, db)
    rule = _make_rule(
        workspace_id=workspace.id,
        keyword=keyword,
        target_category=target_category,
        priority=priority,
        user_id=user_id,
    )
    db.add(rule)
    db.flush()
    applied = _apply_retroactive(
        workspace=workspace, rule=rule, detector=detector, transactions=transactions, db=db
    )
    db.commit()
    _log_rule_created(rule, applied=applied, user_id=user_id)
    return rule_to_response(rule)


def disable_rule(*, workspace_id: str, rule_id: str, db: Session) -> None:
    """Toggle ``enabled=false`` (sem cascade overrides)."""
    rule = db.get(CategorizationRule, rule_id)
    if rule is None or rule.workspace_id != workspace_id or rule.deleted_at is not None:
        raise NotFoundError("Regra não encontrada", code="rule_not_found")
    rule.enabled = False
    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(
        "categorization rule disabled",
        extra={"workspace_id": workspace_id, "rule_id": rule_id},
    )


def _cascade_soft_delete_rule_overrides(
    *, workspace_id: str, rule_id: str, when: datetime, db: Session
) -> None:
    """Soft-delete overrides ``source='rule'`` deste rule_id — preserva histórico."""
    from sqlalchemy import update as sa_update

    db.execute(
        sa_update(TransactionOverride)
        .where(
            TransactionOverride.workspace_id == workspace_id,
            TransactionOverride.rule_id == rule_id,
            TransactionOverride.source == OVERRIDE_SOURCE_RULE,
            TransactionOverride.deleted_at.is_(None),
        )
        .values(deleted_at=when)
    )


def delete_rule(*, workspace_id: str, rule_id: str, db: Session) -> None:
    """Soft-delete rule + cascade overrides ``source='rule'`` (ADR-188 §D1)."""
    rule = db.get(CategorizationRule, rule_id)
    if rule is None or rule.workspace_id != workspace_id or rule.deleted_at is not None:
        raise NotFoundError("Regra não encontrada", code="rule_not_found")
    now = datetime.now(timezone.utc)
    rule.deleted_at = now
    rule.updated_at = now
    _cascade_soft_delete_rule_overrides(workspace_id=workspace_id, rule_id=rule_id, when=now, db=db)
    CategorizationRuleRepository(db).bump_revert_count_rule_disabled(rule_id=rule_id, delta=1)
    db.commit()
    logger.info(
        "categorization rule deleted",
        extra={"workspace_id": workspace_id, "rule_id": rule_id, "mode": "rule_delete"},
    )


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1 or page_size < 1 or page_size > 200:
        raise ValidationError(
            "Paginação inválida: page>=1, 1<=page_size<=200",
            code="invalid_pagination",
        )


def _fetch_active_rules_sorted(
    workspace_id: str,
    enabled: Optional[bool],  # None = sem filtro; True/False filtra enabled
    db: Session,
) -> list[CategorizationRule]:
    base = select(CategorizationRule).where(
        CategorizationRule.workspace_id == workspace_id,
        CategorizationRule.deleted_at.is_(None),
    )
    if enabled is not None:
        base = base.where(CategorizationRule.enabled.is_(enabled))
    rows = db.execute(base).scalars().all()
    return sorted(rows, key=lambda r: (-r.priority, -len(r.keyword), r.created_at))


def _build_list_warnings(*, count_active: int, hard_cap: int) -> list[WarningEntry]:
    if count_active < RULE_SOFT_CAP:
        return []
    return [
        WarningEntry(
            code="near_soft_cap",
            message=f"Workspace tem {count_active} regras (soft cap: {RULE_SOFT_CAP}). "
            f"Considere consolidar antes do hard cap ({hard_cap}).",
        )
    ]


def list_rules(
    *,
    workspace: Workspace,
    enabled: Optional[bool],
    page: int,
    page_size: int,
    db: Session,
) -> RulesListResponse:
    """Lista paginada + meta (count, caps, warnings)."""
    _validate_pagination(page, page_size)
    rows_sorted = _fetch_active_rules_sorted(workspace.id, enabled, db)
    start = (page - 1) * page_size
    page_rows = rows_sorted[start : start + page_size]
    hard_cap = _hard_cap_for(workspace)
    count_active = _count_active_rules(db, workspace.id)
    return RulesListResponse(
        rules=[rule_to_response(r) for r in page_rows],
        meta=RulesListMeta(
            count=count_active,
            soft_cap=RULE_SOFT_CAP,
            hard_cap=hard_cap,
            warnings=_build_list_warnings(count_active=count_active, hard_cap=hard_cap),
        ),
    )


def soft_cap_reached(*, workspace_id: str, db: Session) -> bool:
    """Helper p/ preview — true se workspace já no soft cap."""
    return _count_active_rules(db, workspace_id) >= RULE_SOFT_CAP
