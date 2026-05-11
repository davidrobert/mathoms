"""CRUD ``CategorizationRule`` + thin wrappers ao apply engine (ADR-186/188 · A12 P3 PR2/PR3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.application.categorization import _apply_engine
from backend.app.application.categorization._apply_engine import (
    ApplyTooLargeError as _EngineApplyTooLarge,
)
from backend.app.application.categorization._apply_engine import (
    apply_retroactive_async_safe,
    set_applied_count,
)
from backend.app.application.categorization._apply_engine import (
    count_applied_overrides as _count_applied_overrides,
)
from backend.app.application.categorization._caps import (
    RULE_HARD_CAP,
    RULE_SOFT_CAP,
    SYNC_APPLY_THRESHOLD,
)
from backend.app.application.categorization.mappers import rule_to_response
from backend.app.core.logging import get_logger
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import TransactionOverride
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
from pipeline.domain.services.categorization_service import sort_rules_canonical
from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferDetector,
)

# Re-exports usados por tests (preserva imports legados).
__all__ = [
    "ApplyTooLargeError",
    "HardCapExceededError",
    "RuleAlreadyExistsError",
    "apply_retroactive_async_safe",
    "create_rule",
    "create_rule_async",
    "delete_rule",
    "disable_rule",
    "estimate_apply_matches",
    "list_rules",
    "set_applied_count",
    "soft_cap_reached",
]

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
    """Apply retroativo excede ``SYNC_APPLY_THRESHOLD`` — router (PR3) troca por 202 async."""

    def __init__(self, *, expected_overrides: int) -> None:
        super().__init__(
            f"Apply retroativo síncrono limitado a {SYNC_APPLY_THRESHOLD} overrides; "
            f"esta regra tocaria {expected_overrides}. PR3 implementa async Celery.",
            code="apply_too_large_for_sync",
        )
        self.expected_overrides = expected_overrides


# =============================================================================
# CRUD helpers (DB)
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


def _apply_retroactive(
    *,
    workspace: Workspace,
    rule: CategorizationRule,
    detector: InternalTransferDetector,
    transactions: list,
    db: Session,
) -> int:
    """Thin wrapper sobre engine — traduz ``_EngineApplyTooLarge`` em erro tipado."""
    try:
        return _apply_engine.apply_retroactive_sync(
            workspace_id=workspace.id,
            rule=rule,
            detector=detector,
            transactions=transactions,
            db=db,
        )
    except _EngineApplyTooLarge as exc:
        raise ApplyTooLargeError(expected_overrides=exc.expected_overrides) from exc


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


def create_rule_async(
    *,
    workspace: Workspace,
    keyword: str,
    target_category: str,
    priority: int,
    user_id: Optional[str],
    db: Session,
) -> CategorizationRule:
    """Cria regra **sem** apply retroativo — fluxo 202 PR3 dispara Celery (ADR-188 PR3)."""
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
    db.commit()
    db.refresh(rule)
    logger.info(
        "categorization rule created (async apply pending)",
        extra={
            "workspace_id": rule.workspace_id,
            "rule_id": rule.id,
            "keyword": rule.keyword,
            "target_category": rule.target_category,
            "user_id": user_id,
        },
    )
    return rule


def estimate_apply_matches(
    *,
    keyword: str,
    target_category: str,
    transactions: list,
) -> int:
    """Conta matches sintéticos — usado pelo router p/ decidir sync vs async."""
    return _apply_engine.count_matching(keyword, target_category, transactions)


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

    from backend.app.models.transaction_override import OVERRIDE_SOURCE_RULE

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
    enabled: Optional[bool],  # None = sem filtro; True/False filtra (semântica)
    db: Session,
) -> list[CategorizationRule]:
    base = select(CategorizationRule).where(
        CategorizationRule.workspace_id == workspace_id,
        CategorizationRule.deleted_at.is_(None),
    )
    if enabled is not None:
        base = base.where(CategorizationRule.enabled.is_(enabled))
    rows = db.execute(base).scalars().all()
    # ADR-188 §5 risco #3: sort canônico shared (pipeline domain).
    return list(sort_rules_canonical(rows))


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


# Backwards-compat shim — testes importam ``_count_applied_overrides`` daqui.
__all__.append("_count_applied_overrides")
