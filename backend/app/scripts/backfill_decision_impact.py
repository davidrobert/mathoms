"""Backfill heurístico de ``impact_1y_brl_cents`` em Decisions pré-ADR-179 (ADR-179)."""
# ADR-179 (Sprint A10.3) adicionou ``impact_1y_brl_cents`` /
# ``impact_10y_brl_cents`` ao aggregate. Migration é non-breaking; este
# script popula ``impact_1y_brl_cents`` heuristicamente a partir de
# ``amount_brl_cents`` quando o sinal é forte (aporte mensal × 12,
# valor único Decidido/Executado). Default ``--dry-run``; idempotente.
# ``impact_10y_brl_cents`` permanece manual — extrapolação de 10 anos
# pertence ao consultor, não a script.
#
# Uso:
#     .venv/bin/python -m backend.app.scripts.backfill_decision_impact --dry-run
#     .venv/bin/python -m backend.app.scripts.backfill_decision_impact --apply

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Optional

from sqlalchemy import select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.decision import Decision

# ADR-162 — target_fields cuja semântica é "aporte mensal" (cents/mês).
_MONTHLY_TARGET_FIELDS: frozenset[str] = frozenset(
    {
        "goal.aporte.meta_aporte_mensal_brl",
        "goal.dolar.aporte_mensal_brl",
    }
)

_OTHER_HEURISTIC_STATUSES: frozenset[str] = frozenset({"Decidido", "Executado"})


def _heuristic_impact_1y(decision: Decision) -> Optional[int]:
    """Retorna cents para ``impact_1y_brl_cents`` ou None se sem sinal forte."""
    if decision.amount_brl_cents is None:
        return None
    if decision.target_field in _MONTHLY_TARGET_FIELDS:
        return decision.amount_brl_cents * 12
    if decision.target_field is None and decision.status in _OTHER_HEURISTIC_STATUSES:
        return decision.amount_brl_cents
    return None


def _process_one(decision: Decision, apply: bool) -> bool:
    """Return True se populou ``impact_1y_brl_cents``, False se skip."""
    cents = _heuristic_impact_1y(decision)
    if cents is None:
        print(
            f"  [skip] {decision.id[:8]} ws={decision.workspace_id[:8]} "
            f"code={decision.code} status={decision.status} "
            f"target={decision.target_field!r} amount_cents={decision.amount_brl_cents}",
            flush=True,
        )
        return False
    if apply:
        decision.impact_1y_brl_cents = cents
    print(
        f"  [ok]   {decision.id[:8]} ws={decision.workspace_id[:8]} "
        f"code={decision.code} impact_1y_cents={cents} "
        f"(amount_cents={decision.amount_brl_cents}, target={decision.target_field!r})",
        flush=True,
    )
    return True


async def backfill(apply: bool) -> tuple[int, int, int]:
    """Return ``(total_candidates, populated, skipped)``."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Decision).where(Decision.impact_1y_brl_cents.is_(None)))
        decisions = list(result.scalars().all())
        total = len(decisions)
        print(f"[info] {total} decisions without impact_1y_brl_cents", flush=True)

        populated = sum(_process_one(d, apply) for d in decisions)
        skipped = total - populated

        if apply:
            await db.commit()
            print(f"\n[done] committed {populated} impact_1y values", flush=True)
        else:
            verb = "would commit"
            print(f"\n[dry-run] {verb} {populated} impact_1y values (use --apply)", flush=True)

    return total, populated, skipped


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen (default).",
    )
    g.add_argument("--apply", action="store_true", help="Actually write to DB.")
    args = ap.parse_args()

    apply = bool(args.apply)
    if not apply and not args.dry_run:
        # Default seguro: dry-run sem flag.
        print("[info] no flag passed; defaulting to --dry-run", flush=True)

    total, populated, skipped = asyncio.run(backfill(apply=apply))
    print(f"\nTotal: {total}  Populated: {populated}  Skipped: {skipped}")
    sys.exit(0)


if __name__ == "__main__":
    main()
