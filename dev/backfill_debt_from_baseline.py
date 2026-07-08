#!/usr/bin/env python3
"""Backfill `total_dividas` baseline → rows Debt (ADR-227 §D6 · Sprint A15 Onda 2) — dry-run default; runbook em docs/reference/RUNBOOK.md §10."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


logger = logging.getLogger("debt.backfill")

_BASELINE_STAGES = ("E1.5c", "consolidate_baseline")
_BASELINE_KEY = "baseline_patrimonial"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def _brl_to_cents(value: Any) -> int:
    """BRL → int cents, HALF_UP (ADR-090); evita truncamento silencioso de ``int()`` em fracionários."""
    if value is None:
        return 0
    d = Decimal(str(value))
    cents = (d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def _sum_dividas_for_member(baseline: dict, member_key: str) -> Decimal:
    """Soma ``saldo_31_12`` por substring match (espelha ``patrimonio_resolvers._total_dividas_for``)."""
    dividas_list = baseline.get("dividas", []) or []
    total = Decimal("0")
    needle = member_key.lower()
    for dv in dividas_list:
        prop = (dv.get("proprietario", "") or "").lower()
        if needle and needle in prop:
            saldo = dv.get("saldo_31_12", 0) or 0
            total += Decimal(str(saldo))
    return total


def _read_latest_baseline(session, workspace_id: str) -> Optional[dict]:
    """Busca o artifact baseline mais recente do workspace (legacy ou descritivo)."""
    from backend.app.models import PipelineArtifact
    from backend.app.services.storage.db_artifact_store import _maybe_decrypt

    row = (
        session.query(PipelineArtifact)
        .filter(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage.in_(_BASELINE_STAGES),
            PipelineArtifact.artifact_key == _BASELINE_KEY,
        )
        .order_by(PipelineArtifact.created_at.desc())
        .first()
    )
    if row is None:
        return None
    return _maybe_decrypt(row.content_json)


def _migration_key_exists(session, workspace_id: str, member_key: str) -> bool:
    """`True` se já existe Debt com (workspace_id, migration_source_key) sob o partial unique."""
    from backend.app.models import DEBT_SOURCE_BASELINE_IRPF_MIGRATION, Debt

    key = f"{workspace_id}_{member_key}"
    existing = (
        session.query(Debt)
        .filter(
            Debt.workspace_id == workspace_id,
            Debt.migration_source_key == key,
            Debt.source == DEBT_SOURCE_BASELINE_IRPF_MIGRATION,
        )
        .first()
    )
    return existing is not None


def _build_debt(workspace_id: str, member_key: str, total_brl: Decimal) -> Any:
    """Constrói o objeto Debt (não persistido); caller decide commit."""
    from backend.app.models import DEBT_SOURCE_BASELINE_IRPF_MIGRATION, DEBT_TIPO_OUTRO, Debt

    return Debt(
        workspace_id=workspace_id,
        tipo=DEBT_TIPO_OUTRO,
        descricao=f"Migrado de baseline IRPF ({member_key})",
        saldo_devedor_cents=_brl_to_cents(total_brl),
        source=DEBT_SOURCE_BASELINE_IRPF_MIGRATION,
        migration_source_key=f"{workspace_id}_{member_key}",
        needs_review=True,
    )


def _skip_report(workspace_id: str, reason: str) -> dict:
    return {"workspace_id": workspace_id, "status": "skip", "reason": reason, "members": []}


def _load_members(session, workspace_id: str) -> list[Any]:
    from sqlalchemy import select

    from backend.app.models import FamilyMember

    return list(
        session.execute(
            select(FamilyMember)
            .where(FamilyMember.workspace_id == workspace_id)
            .order_by(FamilyMember.order, FamilyMember.key)
        ).scalars()
    )


def _final_status(dry_run: bool, created_count: int, member_reports: list[dict]) -> str:
    if dry_run:
        return (
            "would_migrate"
            if any(r["action"] == "would_create" for r in member_reports)
            else "noop_dry"
        )
    return "noop" if created_count == 0 else "ok"


def _resolve_workspace_context(session, workspace_id: str) -> dict | tuple[dict, list[Any]]:
    """Retorna skip-report (dict com status='skip') ou tuple (baseline, members)."""
    from sqlalchemy import select

    from backend.app.models import Workspace

    ws = session.execute(select(Workspace).where(Workspace.id == workspace_id)).scalar_one_or_none()
    if ws is None:
        return _skip_report(workspace_id, "not_found")
    baseline = _read_latest_baseline(session, workspace_id)
    if baseline is None:
        return _skip_report(workspace_id, "no_baseline")
    members = _load_members(session, workspace_id)
    if not members:
        return _skip_report(workspace_id, "no_members")
    return baseline, members


def _audit_workspace(session, workspace_id: str, *, dry_run: bool) -> dict:
    """Migra (ou dry-runs) 1 workspace. Retorna report estruturado."""
    ctx = _resolve_workspace_context(session, workspace_id)
    if isinstance(ctx, dict):
        return ctx
    baseline, members = ctx
    member_reports = [
        _process_member(session, workspace_id, m, baseline, dry_run=dry_run) for m in members
    ]
    created_count = sum(1 for r in member_reports if r["action"] == "created")
    if not dry_run and created_count > 0:
        session.commit()
    return {
        "workspace_id": workspace_id,
        "status": _final_status(dry_run, created_count, member_reports),
        "run_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "members": member_reports,
    }


def _process_member(
    session, workspace_id: str, member: Any, baseline: dict, *, dry_run: bool
) -> dict:
    """Decide ação por membro: would_create | created | skipped_already_migrated | skipped_zero."""
    total_brl = _sum_dividas_for_member(baseline, member.key)
    base = {
        "key": member.key,
        "total_dividas_brl": float(total_brl),
        "created_debt_id": None,
    }
    if total_brl <= 0:
        return {**base, "action": "skipped_zero"}
    if _migration_key_exists(session, workspace_id, member.key):
        return {**base, "action": "skipped_already_migrated"}
    if dry_run:
        return {**base, "action": "would_create"}
    debt = _build_debt(workspace_id, member.key, total_brl)
    session.add(debt)
    session.flush()
    return {**base, "action": "created", "created_debt_id": debt.id}


def _emit_audit(reports: list[dict], audit_out: Optional[Path] = None) -> None:
    payload = {"summary_by_status": _summary(reports), "reports": reports}
    output = json.dumps(payload, indent=2, default=str)
    if audit_out is None:
        sys.stdout.write(output + "\n")
        return
    audit_out.parent.mkdir(parents=True, exist_ok=True)
    audit_out.write_text(output + "\n", encoding="utf-8")
    logger.info("audit log → %s", audit_out)


def _summary(reports: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in reports:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


def _resolve_workspace_ids(session, args: argparse.Namespace) -> list[str]:
    """Resolve target workspace_ids do args; raise se nem `--workspace-id` nem `--all-workspaces`."""
    if args.all_workspaces:
        from backend.app.models import Workspace

        rows = session.query(Workspace.id).all()
        return [r[0] for r in rows]
    if args.workspace_id:
        return [args.workspace_id]
    raise SystemExit("error: passe --workspace-id <id> ou --all-workspaces")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--workspace-id", default=None, help="ID do workspace a migrar.")
    group.add_argument("--all-workspaces", action="store_true", help="Migra todos workspaces.")
    parser.add_argument(
        "--apply", action="store_true", help="Persiste rows Debt (default dry-run)."
    )
    parser.add_argument(
        "--audit-out", type=Path, default=None, help="Audit JSON path (default stdout)."
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _setup_logging(args.verbose)

    from backend.app.core.database import SyncSessionLocal

    dry_run = not args.apply
    logger.info("mode: %s", "APPLY" if args.apply else "DRY-RUN")

    reports: list[dict] = []
    with SyncSessionLocal() as session:
        workspace_ids = _resolve_workspace_ids(session, args)
        logger.info("scanning %d workspace(s)", len(workspace_ids))
        for ws_id in workspace_ids:
            report = _audit_workspace(session, ws_id, dry_run=dry_run)
            reports.append(report)
            logger.debug("workspace=%s → status=%s", ws_id, report["status"])

    _emit_audit(reports, args.audit_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
