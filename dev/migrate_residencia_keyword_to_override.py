#!/usr/bin/env python3
"""Cutover migration: `residencia_principal_keyword` → WorkspacePropertyOverride (ADR-215 P6)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


logger = logging.getLogger("residencia.migrate")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def _read_keyword(extra: dict | None) -> Optional[str]:
    if not isinstance(extra, dict):
        return None
    v = extra.get("residencia_principal_keyword")
    if isinstance(v, str) and v.strip():
        return v.strip().lower()
    return None


def _audit_workspace(session, workspace_id: str, dry_run: bool) -> dict:
    """Migra 1 workspace. Retorna report dict."""
    from sqlalchemy import select

    from backend.app.models import (
        CLASSIFICATION_RESIDENCIA_PRINCIPAL,
        OVERRIDE_SOURCE_MIGRATION_KEYWORD,
        RESIDENCIA_STATUS_OWNED,
        FamilyMember,
        PipelineArtifact,
        PropertyIdentity,
        Workspace,
        WorkspacePropertyOverride,
    )

    ws = session.execute(select(Workspace).where(Workspace.id == workspace_id)).scalar_one_or_none()
    if ws is None:
        return {"workspace_id": workspace_id, "status": "skip", "reason": "not_found"}

    titular = session.execute(
        select(FamilyMember).where(
            FamilyMember.workspace_id == workspace_id,
            FamilyMember.role == "titular",
        )
    ).scalar_one_or_none()
    if titular is None:
        return {"workspace_id": workspace_id, "status": "skip", "reason": "no_titular"}

    keyword = _read_keyword(titular.extra)
    if keyword is None:
        return {"workspace_id": workspace_id, "status": "skip", "reason": "no_keyword"}

    existing_override = session.execute(
        select(WorkspacePropertyOverride).where(
            WorkspacePropertyOverride.workspace_id == workspace_id,
            WorkspacePropertyOverride.classification == CLASSIFICATION_RESIDENCIA_PRINCIPAL,
        )
    ).scalar_one_or_none()
    if existing_override is not None:
        return {
            "workspace_id": workspace_id,
            "status": "skip",
            "reason": "already_classified",
            "property_id": existing_override.property_id,
        }

    identities = list(
        session.execute(
            select(PropertyIdentity).where(
                PropertyIdentity.workspace_id == workspace_id,
                PropertyIdentity.titular_key == titular.key,
            )
        ).scalars()
    )

    matches: list[PropertyIdentity] = []
    for ident in identities:
        sample = (ident.descricao_sample or "").lower()
        if keyword in sample:
            matches.append(ident)

    if len(matches) == 1:
        ident = matches[0]
        action = "match_single"
    elif len(matches) > 1:
        action = "ambiguous"
        return {
            "workspace_id": workspace_id,
            "status": "warn",
            "reason": action,
            "keyword": keyword,
            "candidates": [m.id for m in matches],
        }
    else:
        return {
            "workspace_id": workspace_id,
            "status": "warn",
            "reason": "no_match",
            "keyword": keyword,
            "identities_count": len(identities),
        }

    if dry_run:
        return {
            "workspace_id": workspace_id,
            "status": "would_migrate",
            "property_id": ident.id,
            "keyword": keyword,
        }

    now = datetime.now(timezone.utc)
    override = WorkspacePropertyOverride(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        property_id=ident.id,
        classification=CLASSIFICATION_RESIDENCIA_PRINCIPAL,
        override_source=OVERRIDE_SOURCE_MIGRATION_KEYWORD,
        created_by_user_id=None,
        created_at=now,
        updated_at=now,
    )
    session.add(override)
    if ws.residencia_status != RESIDENCIA_STATUS_OWNED:
        ws.residencia_status = RESIDENCIA_STATUS_OWNED
    session.commit()

    return {
        "workspace_id": workspace_id,
        "status": "migrated",
        "property_id": ident.id,
        "keyword": keyword,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persiste (default: dry-run)")
    parser.add_argument(
        "--workspace-id",
        default=None,
        help="Migra apenas 1 workspace (default: todos com keyword setada)",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    from sqlalchemy import select

    from backend.app.core.database import SyncSessionLocal
    from backend.app.models import FamilyMember

    dry_run = not args.apply
    logger.info("migration mode: %s", "APPLY" if args.apply else "DRY-RUN")

    reports: list[dict] = []
    with SyncSessionLocal() as session:
        if args.workspace_id:
            workspace_ids = [args.workspace_id]
        else:
            rows = session.execute(
                select(FamilyMember.workspace_id).where(
                    FamilyMember.role == "titular",
                )
            ).all()
            workspace_ids = [r[0] for r in rows]

        logger.info("scanning %d workspaces", len(workspace_ids))
        for ws_id in workspace_ids:
            report = _audit_workspace(session, ws_id, dry_run=dry_run)
            reports.append(report)
            logger.debug("workspace=%s → %s", ws_id, report)

    by_status: dict[str, int] = {}
    for r in reports:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    json.dump({"summary": by_status, "reports": reports}, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")

    warnings = [r for r in reports if r["status"] == "warn"]
    if warnings:
        logger.warning(
            "%d workspace(s) com keyword sem match limpo — revisar manualmente.",
            len(warnings),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
