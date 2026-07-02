#!/usr/bin/env python3
"""Métricas quantitativas do gate dogfood A12 (RUNBOOK §9.3 · ADR-186 §D6).

Computa, para um workspace real, os 3 critérios mensuráveis da janela de
7 dias de dogfood do Categorization Learning Loop:

1. ≥5 regras persistentes (não-deletadas) criadas na janela.
2. ``revert_rate ≤ 30%`` — sum(revert_count_manual_edit)/sum(applied_count);
   ``revert_count_rule_disabled`` NÃO polui (ADR-188 §D3).
3. ≥3 regras com ≥3 matches retroativos cada (``applied_count ≥ 3``).

Entrevista qualitativa e tempo de confirmação do dialog ficam por conta
do gate humano (RUNBOOK §9.3) — este CLI cobre só o quantitativo.

Uso:
    python3 dev/dogfood_metrics_a12.py --workspace <workspace_id> [--days 7] [--json]
    python3 dev/dogfood_metrics_a12.py --workspace <ws> --since 2026-06-25
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

MIN_RULES = 5
MAX_REVERT_RATE_PCT = 30.0
MIN_RULES_WITH_MATCHES = 3
MIN_MATCHES_PER_RULE = 3


@dataclass(frozen=True)
class RuleMetrics:
    keyword: str
    target_category: str
    applied_count: int
    revert_count_manual_edit: int
    revert_count_rule_disabled: int
    enabled: bool
    created_at: str


@dataclass(frozen=True)
class GateMetrics:
    workspace_id: str
    window_start: str
    rules_persistent: int
    applied_total: int
    reverts_manual_edit_total: int
    revert_rate_pct: Optional[float]  # None quando applied_total == 0
    rules_with_min_matches: int
    criteria: dict
    verdict: str  # PASS | PARTIAL | FAIL
    rules: list


def _load_rules(session, workspace_id: str, since: datetime) -> list:
    from sqlalchemy import select

    from backend.app.models.categorization_rule import CategorizationRule

    stmt = select(CategorizationRule).where(
        CategorizationRule.workspace_id == workspace_id,
        CategorizationRule.deleted_at.is_(None),
        CategorizationRule.created_at >= since,
    )
    return list(session.execute(stmt).scalars().all())


def _rule_metrics(rule) -> RuleMetrics:
    return RuleMetrics(
        keyword=rule.keyword,
        target_category=rule.target_category,
        applied_count=rule.applied_count,
        revert_count_manual_edit=rule.revert_count_manual_edit,
        revert_count_rule_disabled=rule.revert_count_rule_disabled,
        enabled=rule.enabled,
        created_at=rule.created_at.isoformat() if rule.created_at else "",
    )


def _verdict(criteria: dict) -> str:
    passed = sum(1 for ok in criteria.values() if ok)
    if passed == len(criteria):
        return "PASS"
    return "PARTIAL" if passed > 0 else "FAIL"


def _criteria(rules: list, rate: Optional[float] = None, *, with_matches: int = 0) -> dict:
    return {
        f"rules_persistent >= {MIN_RULES}": len(rules) >= MIN_RULES,
        f"revert_rate <= {MAX_REVERT_RATE_PCT}%": rate is not None and rate <= MAX_REVERT_RATE_PCT,
        f">={MIN_RULES_WITH_MATCHES} rules com >={MIN_MATCHES_PER_RULE} matches": (
            with_matches >= MIN_RULES_WITH_MATCHES
        ),
    }


def compute_metrics(session, workspace_id: str, since: datetime) -> GateMetrics:
    """Critérios §9.3 sobre as regras vivas do workspace criadas desde ``since``."""
    rules = [_rule_metrics(r) for r in _load_rules(session, workspace_id, since)]
    applied = sum(r.applied_count for r in rules)
    reverts = sum(r.revert_count_manual_edit for r in rules)
    rate = round(reverts / applied * 100, 2) if applied > 0 else None
    with_matches = sum(1 for r in rules if r.applied_count >= MIN_MATCHES_PER_RULE)
    criteria = _criteria(rules, rate, with_matches=with_matches)
    return GateMetrics(
        workspace_id=workspace_id,
        window_start=since.isoformat(),
        rules_persistent=len(rules),
        applied_total=applied,
        reverts_manual_edit_total=reverts,
        revert_rate_pct=rate,
        rules_with_min_matches=with_matches,
        criteria=criteria,
        verdict=_verdict(criteria),
        rules=[asdict(r) for r in rules],
    )


def _print_report(m: GateMetrics) -> None:
    print(f"# Dogfood A12 — métricas §9.3 · workspace {m.workspace_id}")
    print(f"Janela desde: {m.window_start}")
    print(f"Regras persistentes: {m.rules_persistent}")
    rate = f"{m.revert_rate_pct}%" if m.revert_rate_pct is not None else "N/D (0 applied)"
    print(
        f"Revert rate (manual_edit/applied): {rate} ({m.reverts_manual_edit_total}/{m.applied_total})"
    )
    print(f"Regras com >={MIN_MATCHES_PER_RULE} matches: {m.rules_with_min_matches}")
    print()
    for name, ok in m.criteria.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\nVeredito: {m.verdict}")
    print("Entrevista qualitativa (3 perguntas) + tempo de dialog: gate humano (RUNBOOK §9.3).")


def _resolve_since(args) -> datetime:
    if args.since:
        return datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - timedelta(days=args.days)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="workspace_id do dogfood user")
    parser.add_argument("--days", type=int, default=7, help="janela em dias (default 7)")
    parser.add_argument("--since", help="início da janela (ISO date, sobrepõe --days)")
    parser.add_argument("--json", action="store_true", help="emite JSON em vez de texto")
    args = parser.parse_args()

    from backend.app.core.database import SyncSessionLocal

    since = _resolve_since(args)
    with SyncSessionLocal() as session:
        metrics = compute_metrics(session, args.workspace, since)
    if args.json:
        print(json.dumps(asdict(metrics), ensure_ascii=False, indent=2))
    else:
        _print_report(metrics)
    return 0 if metrics.verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
