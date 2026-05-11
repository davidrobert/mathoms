"""Avaliação de invariantes do gate técnico."""

from __future__ import annotations

from sqlalchemy import select

from backend.app.application.categorization import _apply_engine
from backend.app.application.categorization._caps import KEYWORD_TOO_SHORT_THRESHOLD
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    TransactionOverride,
)
from dev._dogfood_gate_a12.rule_ops import sync_db_ctx
from dev._dogfood_gate_a12.types import GateInvariant, RuleResult


def _short_keyword_target(rules: list[RuleResult]) -> RuleResult | None:
    return next((r for r in rules if len(r.keyword) < KEYWORD_TOO_SHORT_THRESHOLD), None)


def eval_keyword_too_short(rules: list[RuleResult]) -> GateInvariant:
    target = _short_keyword_target(rules)
    if target is None:
        return GateInvariant(
            code="keyword_too_short_warning",
            description=f"Preview emite keyword_too_short para keyword < {KEYWORD_TOO_SHORT_THRESHOLD}",
            status="N/A",
            detail="bateria não incluiu keyword curta",
        )
    has = "keyword_too_short" in target.preview_warnings
    return GateInvariant(
        code="keyword_too_short_warning",
        description=f"Preview emite keyword_too_short quando keyword < {KEYWORD_TOO_SHORT_THRESHOLD} chars",
        status="PASS" if has else "FAIL",
        detail=(
            f"keyword={target.keyword!r} ({len(target.keyword)} chars); "
            f"warnings={target.preview_warnings}"
        ),
    )


def eval_blacklist_internal_transfer(rules: list[RuleResult]) -> GateInvariant:
    pix_rule = next((r for r in rules if r.keyword.upper() == "PIX"), None)
    if pix_rule is None:
        return GateInvariant(
            code="blacklist_internal_transfer",
            description="Regra PIX → matches_blocked_internal_transfers > 0",
            status="N/A",
            detail="bateria sem regra PIX",
        )
    ok = pix_rule.preview_blocked_internal_transfers > 0
    return GateInvariant(
        code="blacklist_internal_transfer",
        description="Preview reporta matches_blocked_internal_transfers > 0 para keyword PIX",
        status="PASS" if ok else "FAIL",
        detail=(
            f"matches_total={pix_rule.preview_matches_total} "
            f"blocked={pix_rule.preview_blocked_internal_transfers}"
        ),
    )


def eval_closed_months_split(rules: list[RuleResult]) -> GateInvariant:
    with_closed = [r for r in rules if r.preview_in_closed_months > 0]
    ok = bool(with_closed)
    return GateInvariant(
        code="closed_months_split",
        description="Preview mostra closed > 0 em pelo menos 1 regra (com 2 meses fechados)",
        status="PASS" if ok else "FAIL",
        detail=f"regras com closed > 0: {[(r.keyword, r.preview_in_closed_months) for r in with_closed]}",
    )


def _count_preserved_manual_overrides(sync_db, ws_id: str) -> int:
    rows = (
        sync_db.execute(
            select(TransactionOverride).where(
                TransactionOverride.workspace_id == ws_id,
                TransactionOverride.source == OVERRIDE_SOURCE_MANUAL,
                TransactionOverride.deleted_at.is_(None),
                TransactionOverride.new_category == "Categoria Manual Crítica",
            )
        )
        .scalars()
        .all()
    )
    return len(rows)


def _sticky_status(preserved: int, seeded: int) -> str:
    if seeded == 0:
        return "WARN"
    return "PASS" if preserved == seeded else "FAIL"


def eval_sticky_manual(ws_id: str, manual_seeded: int) -> GateInvariant:
    with sync_db_ctx() as sync_db:
        preserved = _count_preserved_manual_overrides(sync_db, ws_id)
    return GateInvariant(
        code="sticky_manual_override",
        description="Manual overrides pré-existentes preservam source=manual + new_category",
        status=_sticky_status(preserved, manual_seeded),
        detail=f"seeded={manual_seeded}; preserved_after_apply={preserved}",
    )


def _alignment_for_rule(
    sync_db, ws_id: str, r: RuleResult, reverts_per_rule: dict[str, int]
) -> tuple[str, int, int, int] | None:
    if r.rule_id is None:
        return None
    db_count = _apply_engine.count_applied_overrides(sync_db, ws_id, r.rule_id)
    rule_row = sync_db.get(CategorizationRule, r.rule_id)
    if rule_row is None:
        return None
    reverts = reverts_per_rule.get(r.rule_id, 0)
    expected = rule_row.applied_count - reverts
    if expected != db_count:
        return (r.keyword, rule_row.applied_count, reverts, db_count)
    return None


_ALIGNMENT_DESC = (
    "rule.applied_count - revert_count_manual_edit == "
    "COUNT(transaction_overrides ativos source=rule por rule_id)"
)


def _collect_alignment_mismatches(
    rules: list[RuleResult], ws_id: str, reverts_per_rule: dict[str, int]
) -> list[tuple[str, int, int, int]]:
    mismatches: list[tuple[str, int, int, int]] = []
    with sync_db_ctx() as sync_db:
        for r in rules:
            m = _alignment_for_rule(sync_db, ws_id, r, reverts_per_rule)
            if m is not None:
                mismatches.append(m)
    return mismatches


def eval_applied_count_alignment(
    rules: list[RuleResult], ws_id: str, reverts_per_rule: dict[str, int]
) -> GateInvariant:
    """applied_count - reverts == COUNT(rule overrides ativos). Histórico não decrementa."""
    mismatches = _collect_alignment_mismatches(rules, ws_id, reverts_per_rule)
    detail = (
        "aligned"
        if not mismatches
        else f"mismatches (kw, applied, reverts, db_count): {mismatches}"
    )
    return GateInvariant(
        code="applied_count_alignment",
        description=_ALIGNMENT_DESC,
        status="PASS" if not mismatches else "FAIL",
        detail=detail,
    )


def _check_revert_below_expected(
    sync_db, reverts_per_rule: dict[str, int]
) -> list[tuple[str, int, int]]:
    bad: list[tuple[str, int, int]] = []
    for rule_id, expected in reverts_per_rule.items():
        rule = sync_db.get(CategorizationRule, rule_id)
        if rule is None:
            continue
        actual = rule.revert_count_manual_edit or 0
        if actual < expected:
            bad.append((rule.keyword, actual, expected))
    return bad


def eval_revert_count_manual_edit(reverts_per_rule: dict[str, int]) -> GateInvariant:
    if not reverts_per_rule:
        return GateInvariant(
            code="revert_count_manual_edit_bumps",
            description="revert_count_manual_edit bumpa quando override rule → manual divergente",
            status="N/A",
            detail="nenhum revert simulado",
        )
    with sync_db_ctx() as sync_db:
        bad = _check_revert_below_expected(sync_db, reverts_per_rule)
    return GateInvariant(
        code="revert_count_manual_edit_bumps",
        description="revert_count_manual_edit refletiu reverts simulados",
        status="PASS" if not bad else "FAIL",
        detail="ok" if not bad else f"below expected: {bad}",
    )


def eval_revert_rate(rules: list[RuleResult], reverts_per_rule: dict[str, int]) -> GateInvariant:
    """revert_rate ≤ 30% (gate dogfood ADR-186 §D6) — computabilidade do KPI."""
    total_applied = sum(r.create_applied_count for r in rules)
    total_reverts = sum(reverts_per_rule.values()) if reverts_per_rule else 0
    if total_applied == 0:
        return GateInvariant(
            code="revert_rate_threshold",
            description="revert_rate ≤ 30%",
            status="N/A",
            detail="zero overrides aplicados",
        )
    rate = total_reverts / total_applied
    return GateInvariant(
        code="revert_rate_threshold",
        description="revert_rate ≤ 30% (gate dogfood ADR-186 §D6)",
        status="PASS" if rate <= 0.30 else "FAIL",
        detail=f"rate={rate:.2%} (reverts={total_reverts}, applied={total_applied})",
    )


def eval_rules_with_threshold_matches(
    rules: list[RuleResult], min_matches: int = 3
) -> GateInvariant:
    qualifying = [r for r in rules if r.create_applied_count >= min_matches]
    return GateInvariant(
        code="rules_with_threshold_matches",
        description=f"≥3 regras com ≥{min_matches} matches retroativos cada",
        status="PASS" if len(qualifying) >= 3 else "FAIL",
        detail=f"qualifying={[(r.keyword, r.create_applied_count) for r in qualifying]}",
    )


def eval_minimum_rules_persistent(rules: list[RuleResult]) -> GateInvariant:
    persisted = [r.keyword for r in rules if r.create_status == "ok"]
    return GateInvariant(
        code="minimum_rules_persistent",
        description="≥5 regras criadas com sucesso (gate dogfood ADR-186 §D6)",
        # WARN, não FAIL: fixture esperada produz PASS; gate humano cria as regras.
        status="PASS" if len(persisted) >= 5 else "WARN",
        detail=f"persisted={persisted}",
    )


__all__ = [
    "eval_applied_count_alignment",
    "eval_blacklist_internal_transfer",
    "eval_closed_months_split",
    "eval_keyword_too_short",
    "eval_minimum_rules_persistent",
    "eval_revert_count_manual_edit",
    "eval_revert_rate",
    "eval_rules_with_threshold_matches",
    "eval_sticky_manual",
]
