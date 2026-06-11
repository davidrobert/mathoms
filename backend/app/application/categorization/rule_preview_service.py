"""``preview_rule`` — preview de regra sem persistir (ADR-186/188 §D5 · A12 P3 PR2)."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.application.categorization._caps import (
    KEYWORD_TOO_SHORT_THRESHOLD,
)
from backend.app.core.logging import get_logger
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    TransactionOverride,
)
from backend.app.schemas.dto.categorization_rule import (
    ConflictEntry,
    RulePreviewResponse,
    WarningEntry,
)
from backend.app.schemas.transactions import TransactionItem
from backend.app.services.feature_flags_service import is_enabled_sync
from backend.app.services.override_dual_read import (
    OVERRIDE_NATURAL_KEY_V2_FLAG,
    OverrideMatchIndex,
)
from backend.app.services.report_publication import is_month_closed_sync
from backend.app.services.transaction_service import natural_key_for_match
from pipeline.domain.services.categorization_service import (
    CategorizationRulesV2,
    LearnedRule,
    normalize_narrative,
)
from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferConfig,
    InternalTransferDetector,
)

logger = get_logger("categorization.preview")


@dataclass(frozen=True)
class _MatchAccumulator:
    """Mutable-ish accumulator wrapped em dataclass (estilo: monta dict só no final)."""

    matches_total: int
    matches_in_closed_months: int
    matches_with_manual_override: int
    matches_blocked_internal_transfers: int
    matches_amount_total_brl_cents: int
    matches_by_month: dict[str, int]


def _period_from_data(data_str: str) -> Optional[str]:
    """``YYYYMM`` extraído de ISO ``YYYY-MM-DD`` — paridade learning_loop."""
    if not data_str or len(data_str) < 7:
        return None
    yyyy, mm = data_str[:4], data_str[5:7]
    if not (yyyy.isdigit() and mm.isdigit()):
        return None
    return f"{yyyy}{mm}"


def _decimal_to_cents(value: Decimal) -> int:
    """Money em cents (ADR-090). ``valor`` no E4 é Decimal positivo (despesa) ou positivo (receita)."""
    return int((Decimal(value) * Decimal(100)).quantize(Decimal("1")))


def _build_synthetic_rules(keyword: str, target_category: str) -> CategorizationRulesV2:
    """Cria ``CategorizationRulesV2`` com 1 regra sintética + template vazio."""
    synthetic = LearnedRule(
        id="preview",
        keyword=keyword.upper(),
        target_category=target_category,
        priority=100,
        created_at=datetime.now(timezone.utc),
    )
    return CategorizationRulesV2.from_template_and_learned(
        template_keywords={},
        learned_rules=(synthetic,),
    )


def _load_active_manual_index(
    db: Session, workspace_id: str, *, v2_enabled: bool
) -> OverrideMatchIndex:
    """Overrides manuais ativos (sticky no apply) — dual-read v2→v1 (ADR-282)."""
    rows = (
        db.execute(
            select(TransactionOverride)
            .where(
                TransactionOverride.workspace_id == workspace_id,
                TransactionOverride.source == OVERRIDE_SOURCE_MANUAL,
                TransactionOverride.deleted_at.is_(None),
            )
            .order_by(TransactionOverride.created_at, TransactionOverride.id)
        )
        .scalars()
        .all()
    )
    return OverrideMatchIndex.from_overrides(rows, workspace_id=workspace_id, v2_enabled=v2_enabled)


def _load_active_conflicts(db: Session, workspace_id: str, keyword: str) -> list[ConflictEntry]:
    """Regras ativas que usam a mesma keyword (UI alerta antes de criar)."""
    stmt = select(CategorizationRule).where(
        CategorizationRule.workspace_id == workspace_id,
        CategorizationRule.keyword == keyword,
        CategorizationRule.enabled.is_(True),
        CategorizationRule.deleted_at.is_(None),
    )
    rows = db.execute(stmt).scalars().all()
    return [
        ConflictEntry(rule_id=r.id, target_category=r.target_category, priority=r.priority)
        for r in rows
    ]


def _within_window(
    period: Optional[str],  # None se tx.data não parseável
    window: Optional[tuple[str, str]],  # None = sem filtro; (start,end) inclusivo
) -> bool:
    """``True`` se o período da txn (YYYYMM) cai dentro da janela inclusiva."""
    if window is None:
        return True
    if period is None:
        return False
    return window[0] <= period <= window[1]


@dataclass
class _PreviewCtx:
    """Contexto agrupado (R9 — evita listas longas de args)."""

    workspace_id: str
    rules: CategorizationRulesV2
    manual_index: OverrideMatchIndex
    detector: InternalTransferDetector
    closed_cache: dict[str, bool]
    db: Session


def _is_match(tx: TransactionItem, ctx: _PreviewCtx) -> bool:
    """``True`` se a regra casa — usa ``normalize_narrative`` 1×/tx (PR3 R1)."""
    return ctx.rules.match_normalized(normalize_narrative(tx.descricao)) is not None


def _classify_match(
    tx: TransactionItem,
    ctx: _PreviewCtx,
) -> tuple[bool, bool, bool, Optional[str]]:
    """``(in_closed, with_manual, blocked_transfer, period)`` para 1 match."""
    period = _period_from_data(tx.data)
    in_closed = False
    if period is not None:
        if period not in ctx.closed_cache:
            ctx.closed_cache[period] = is_month_closed_sync(ctx.workspace_id, period, db=ctx.db)
        in_closed = ctx.closed_cache[period]
    with_manual = (
        ctx.manual_index.match(
            natural_key_hash=natural_key_for_match(tx, ctx.manual_index),
            legacy_hash=tx.transaction_hash,
        )
        is not None
    )
    blocked_transfer = ctx.detector.is_internal_transfer(tx.descricao or "", banco=tx.banco or "")
    return in_closed, with_manual, blocked_transfer, period


@dataclass
class _Tally:
    """Estado mutável da acumulação (refatorado de _accumulate p/ ≤20 lines)."""

    matches_total: int = 0
    in_closed: int = 0
    with_manual: int = 0
    blocked_transfer: int = 0
    amount_cents: int = 0
    by_month: Counter[str] = field(default_factory=Counter)

    def freeze(self) -> _MatchAccumulator:
        return _MatchAccumulator(
            matches_total=self.matches_total,
            matches_in_closed_months=self.in_closed,
            matches_with_manual_override=self.with_manual,
            matches_blocked_internal_transfers=self.blocked_transfer,
            matches_amount_total_brl_cents=self.amount_cents,
            matches_by_month=dict(self.by_month),
        )


def _tally_one(
    tx: TransactionItem,
    period: Optional[str],  # None = tx.data inválida (não bumpa by_month)
    ctx: _PreviewCtx,
    tally: _Tally,
) -> None:
    tally.matches_total += 1
    is_closed, is_manual, is_transfer, _ = _classify_match(tx, ctx)
    if is_closed:
        tally.in_closed += 1
    if is_manual:
        tally.with_manual += 1
    if is_transfer:
        tally.blocked_transfer += 1
    tally.amount_cents += abs(_decimal_to_cents(tx.valor))
    if period:
        tally.by_month[period] += 1


def _accumulate(
    transactions: Iterable[TransactionItem],
    ctx: _PreviewCtx,
    window: Optional[tuple[str, str]],  # None = preview em toda a base
) -> _MatchAccumulator:
    """Itera transações, contabiliza matches por categoria de bloqueio."""
    tally = _Tally()
    for tx in transactions:
        if not _is_match(tx, ctx):
            continue
        period = _period_from_data(tx.data)
        if not _within_window(period, window):
            continue
        _tally_one(tx, period, ctx, tally)
    return tally.freeze()


def _warning_keyword_too_short(keyword: str) -> Optional[WarningEntry]:
    if len(keyword) >= KEYWORD_TOO_SHORT_THRESHOLD:
        return None
    return WarningEntry(
        code="keyword_too_short",
        message=f"Keyword muito curta ({len(keyword)} chars). "
        f"Mínimo recomendado: {KEYWORD_TOO_SHORT_THRESHOLD} chars.",
    )


def _warning_near_soft_cap(soft_cap_reached: bool) -> Optional[WarningEntry]:
    if not soft_cap_reached:
        return None
    return WarningEntry(
        code="near_soft_cap",
        message="Workspace próximo do soft cap de regras (50). Considere consolidar.",
    )


def _build_warnings(keyword: str, soft_cap_reached: bool) -> list[WarningEntry]:
    """Warnings UI-friendly (não-bloqueante)."""
    candidates = (_warning_keyword_too_short(keyword), _warning_near_soft_cap(soft_cap_reached))
    return [w for w in candidates if w is not None]


def _is_low_risk(acc: _MatchAccumulator, conflicts: list[ConflictEntry]) -> bool:
    return (
        acc.matches_in_closed_months == 0
        and acc.matches_with_manual_override == 0
        and acc.matches_blocked_internal_transfers == 0
        and not conflicts
    )


def _requires_confirmation(acc: _MatchAccumulator) -> bool:
    """PR2: há match em mês aberto. P4 refina com ``month_view_log``."""
    return acc.matches_total > 0 and (acc.matches_total - acc.matches_in_closed_months) > 0


def _preview_log_extra(
    *,
    workspace_id: str,
    keyword: str,
    target_category: str,
    acc: _MatchAccumulator,
    conflicts_count: int,
    low_risk: bool,
) -> dict:
    return {
        "workspace_id": workspace_id,
        "keyword": keyword,
        "target_category": target_category,
        "matches_total": acc.matches_total,
        "matches_in_closed_months": acc.matches_in_closed_months,
        "matches_with_manual_override": acc.matches_with_manual_override,
        "matches_blocked_internal_transfers": acc.matches_blocked_internal_transfers,
        "conflicts_count": conflicts_count,
        "low_risk": low_risk,
    }


def _log_preview(**kwargs) -> None:
    logger.info("categorization preview run", extra=_preview_log_extra(**kwargs))


def _build_preview_response(
    *,
    acc: _MatchAccumulator,
    conflicts: list[ConflictEntry],
    warnings: list[WarningEntry],
) -> RulePreviewResponse:
    return RulePreviewResponse(
        matches_total=acc.matches_total,
        matches_in_closed_months=acc.matches_in_closed_months,
        matches_with_manual_override=acc.matches_with_manual_override,
        matches_blocked_internal_transfers=acc.matches_blocked_internal_transfers,
        matches_amount_total_brl_cents=acc.matches_amount_total_brl_cents,
        matches_by_month=acc.matches_by_month,
        conflicts=conflicts,
        low_risk=_is_low_risk(acc, conflicts),
        requires_user_confirmation=_requires_confirmation(acc),
        warnings=warnings,
    )


def _build_preview_ctx(
    *,
    workspace_id: str,
    keyword: str,
    target_category: str,
    detector: InternalTransferDetector,
    db: Session,
) -> _PreviewCtx:
    v2_enabled = is_enabled_sync(workspace_id, OVERRIDE_NATURAL_KEY_V2_FLAG, db=db)
    return _PreviewCtx(
        workspace_id=workspace_id,
        rules=_build_synthetic_rules(keyword, target_category),
        manual_index=_load_active_manual_index(db, workspace_id, v2_enabled=v2_enabled),
        detector=detector,
        closed_cache={},
        db=db,
    )


def preview_rule(
    *,
    workspace_id: str,
    keyword: str,
    target_category: str,
    period_window: Optional[tuple[str, str]],
    transactions: list,
    db: Session,
    detector: InternalTransferDetector,
    soft_cap_reached: bool = False,
) -> RulePreviewResponse:
    """Roda regra sintética contra transações; retorna shape rico (ADR-188 §D5)."""
    ctx = _build_preview_ctx(
        workspace_id=workspace_id,
        keyword=keyword,
        target_category=target_category,
        detector=detector,
        db=db,
    )
    conflicts = _load_active_conflicts(db, workspace_id, keyword)
    acc = _accumulate(transactions, ctx, period_window)
    warnings = _build_warnings(keyword, soft_cap_reached)
    response = _build_preview_response(acc=acc, conflicts=conflicts, warnings=warnings)
    _log_preview(
        workspace_id=workspace_id,
        keyword=keyword,
        target_category=target_category,
        acc=acc,
        conflicts_count=len(conflicts),
        low_risk=response.low_risk,
    )
    return response


# Re-export para uso em rule_management_service (DRY).
def build_synthetic_rules(keyword: str, target_category: str) -> CategorizationRulesV2:
    """Helper exportado — service de criação reusa o mesmo builder."""
    return _build_synthetic_rules(keyword, target_category)


def period_from_data(data_str: str) -> Optional[str]:
    """Helper exportado para reuso em rule_management_service."""
    return _period_from_data(data_str)


def decimal_to_cents(value: Decimal) -> int:
    """Helper exportado (money cents)."""
    return _decimal_to_cents(value)


# Pure helpers usados na inicialização do detector (mocking-friendly).
def empty_detector() -> InternalTransferDetector:
    """Detector vazio — fallback usado em testes sem config de banco."""
    return InternalTransferDetector(InternalTransferConfig())


# Mantém uuid import (evita unused-import — ID de override no rule mgmt usa).
_ = uuid
