"""Pipeline orquestrador — junta seed + bateria + reverts + caps + invariantes."""

from __future__ import annotations

from typing import Any

from backend.app.application.categorization._caps import RULE_HARD_CAP
from backend.app.core.database import async_session
from dev._dogfood_gate_a12 import caps, invariants
from dev._dogfood_gate_a12.fixture import (
    RNG,
    build_detector,
    gen_all_items,
    gen_periods_24_months,
)
from dev._dogfood_gate_a12.reverts import simulate_reverts
from dev._dogfood_gate_a12.rule_ops import attempt_create_rule, load_txs
from dev._dogfood_gate_a12.seed import (
    close_months,
    create_schema,
    seed_e4_artifact_with_items,
    seed_manual_overrides_sync,
    seed_workspace,
)
from dev._dogfood_gate_a12.types import GateInvariant, GateReport, RuleResult


async def async_setup() -> tuple[str, str, int, list[str]]:
    """Cria schema + workspace + artefatos + fecha 2 meses."""
    await create_schema()
    async with async_session() as db:
        user_id, ws_id = await seed_workspace(db)
        periods = gen_periods_24_months()
        items = gen_all_items(periods)
        await seed_e4_artifact_with_items(db, ws_id, items)
        closed = periods[:2]
        await close_months(db, ws_id, closed)
    return user_id, ws_id, len(items), closed


def _tx_to_payload(tx) -> dict:
    return {
        "data": tx.data,
        "descricao": tx.descricao,
        "valor": str(tx.valor),
        "banco": tx.banco,
        "categoria": tx.categoria,
        "titular": tx.titular,
    }


def pick_manual_override_txs(ws_id: str, n: int = 5) -> list[dict]:
    """N transações aleatórias do conjunto carregado p/ manual override prévio."""
    transactions = load_txs(ws_id)
    if not transactions:
        return []
    sample = RNG.sample(transactions, min(n, len(transactions)))
    return [_tx_to_payload(tx) for tx in sample]


_BATTERY: tuple[tuple[str, str], ...] = (
    ("IFOOD", "Alimentação"),
    ("MERCADOLIVRE", "Compras"),
    ("UBER", "Transporte"),
    ("PIX", "Transferência"),
    ("13", "Receita Variável"),
)


def run_main_battery(ws_id: str, user_id: str, detector) -> list[RuleResult]:
    return [
        attempt_create_rule(
            ws_id=ws_id, user_id=user_id, keyword=kw, target_category=cat, detector=detector
        )
        for kw, cat in _BATTERY
    ]


_BLOCKED_STATUSES = frozenset({"conflict", "cap", "async_required", "error"})


def build_metrics(rules: list[RuleResult]) -> dict[str, Any]:
    total_preview = sum(r.preview_matches_total for r in rules)
    total_apply = sum(r.create_applied_count for r in rules)
    ratio = (total_apply / total_preview) if total_preview else 0.0
    return {
        "total_preview_matches": total_preview,
        "total_applied_overrides": total_apply,
        "apply_preview_ratio": round(ratio, 3),
        "rules_attempted": len(rules),
        "rules_created_ok": sum(1 for r in rules if r.create_status == "ok"),
        "rules_async_path": sum(1 for r in rules if r.create_async_path),
        "rules_blocked": sum(1 for r in rules if r.create_status in _BLOCKED_STATUSES),
    }


def verdict(invariants_list: list[GateInvariant]) -> str:
    fails = [i for i in invariants_list if i.status == "FAIL"]
    if not fails:
        return "PASS"
    if len(fails) <= 2:
        return "PARTIAL"
    return "FAIL"


def _eval_battery_invariants(rules: list[RuleResult]) -> list[GateInvariant]:
    return [
        invariants.eval_minimum_rules_persistent(rules),
        invariants.eval_rules_with_threshold_matches(rules),
        invariants.eval_keyword_too_short(rules),
        invariants.eval_blacklist_internal_transfer(rules),
        invariants.eval_closed_months_split(rules),
    ]


def _eval_persistence_invariants(
    rules: list[RuleResult], ws_id: str, manual_seeded: int, reverts_per_rule: dict[str, int]
) -> list[GateInvariant]:
    return [
        invariants.eval_sticky_manual(ws_id, manual_seeded),
        invariants.eval_applied_count_alignment(rules, ws_id, reverts_per_rule),
        invariants.eval_revert_count_manual_edit(reverts_per_rule),
        invariants.eval_revert_rate(rules, reverts_per_rule),
    ]


def _build_invariants(
    rules: list[RuleResult],
    ws_id: str,
    manual_seeded: int,
    reverts_per_rule: dict[str, int],
    soft_cap_inv: GateInvariant,
    hard_cap_inv: GateInvariant,
) -> list[GateInvariant]:
    return [
        *_eval_battery_invariants(rules),
        *_eval_persistence_invariants(rules, ws_id, manual_seeded, reverts_per_rule),
        soft_cap_inv,
        hard_cap_inv,
    ]


def _enrich_metrics(metrics: dict[str, Any], reverts_per_rule: dict[str, int]) -> None:
    metrics["reverts_simulated"] = sum(reverts_per_rule.values()) if reverts_per_rule else 0
    metrics["rules_after_cap_seed"] = RULE_HARD_CAP


def _run_battery_and_reverts(
    ws_id: str, user_id: str, detector
) -> tuple[int, list[RuleResult], dict[str, int]]:
    manual_txs = pick_manual_override_txs(ws_id, n=5)
    manual_seeded = seed_manual_overrides_sync(ws_id, manual_txs)
    rules = run_main_battery(ws_id, user_id, detector)
    reverts_per_rule = simulate_reverts(ws_id)
    return manual_seeded, rules, reverts_per_rule


def _assemble_report(
    *,
    ws_id: str,
    closed: list[str],
    total_txs: int,
    manual_seeded: int,
    rules: list[RuleResult],
    invariants_list: list[GateInvariant],
    metrics: dict[str, Any],
) -> GateReport:
    return GateReport(
        verdict=verdict(invariants_list),
        workspace_id=ws_id,
        total_transactions=total_txs,
        closed_months=closed,
        manual_overrides_seeded=manual_seeded,
        rules=rules,
        invariants=invariants_list,
        metrics=metrics,
    )


def run_pipeline_sync(ws_id: str, user_id: str, closed: list[str], total_txs: int) -> GateReport:
    """Bloco sync — bateria + reverts + caps + invariantes + métricas."""
    detector = build_detector()
    manual_seeded, rules, reverts_per_rule = _run_battery_and_reverts(ws_id, user_id, detector)
    soft_cap_inv = caps.test_soft_cap_warning(ws_id, detector)
    hard_cap_inv = caps.test_hard_cap_block(ws_id, user_id, detector)
    invariants_list = _build_invariants(
        rules, ws_id, manual_seeded, reverts_per_rule, soft_cap_inv, hard_cap_inv
    )
    metrics = build_metrics(rules)
    _enrich_metrics(metrics, reverts_per_rule)
    return _assemble_report(
        ws_id=ws_id,
        closed=closed,
        total_txs=total_txs,
        manual_seeded=manual_seeded,
        rules=rules,
        invariants_list=invariants_list,
        metrics=metrics,
    )


__all__ = ["async_setup", "run_pipeline_sync", "verdict"]
