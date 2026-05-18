#!/usr/bin/env python3
"""Cleanup: dedupa property_identity rows existentes pós fix-B2 (ADR-215).

Para workspaces que rodaram E1.5c antes do fix-B2, pode haver 2+ rows
com mesmo `(workspace_id, codigo_rfb, endereco_canonical)` — uma por
titular distinto. Esse script consolida em 1 row (first-write wins),
realocando `workspace_property_overrides.property_id` para a canônica.

Idempotente. Dry-run por default.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MATHOMS_FERNET_KEY", "gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0=")
os.environ.setdefault("MATHOMS_JWT_SECRET", "x" * 32)
os.environ.setdefault("MATHOMS_REGISTER_RATE_LIMIT_PER_HOUR", "0")


def _group_by_canonical(rows) -> dict:
    groups: dict[tuple[str, str], list] = defaultdict(list)
    for r in rows:
        if r.endereco_canonical is None:
            continue
        groups[(r.codigo_rfb, r.endereco_canonical)].append(r)
    return groups


def _realocate_overrides(session, dupe_id: str, canonical_id: str, dry_run: bool) -> int:
    from sqlalchemy import select

    from backend.app.models import WorkspacePropertyOverride

    stmt = select(WorkspacePropertyOverride).where(WorkspacePropertyOverride.property_id == dupe_id)
    count = 0
    for ovr in session.execute(stmt).scalars():
        if not dry_run:
            ovr.property_id = canonical_id
        count += 1
    return count


def _merge_group(session, members: list, dry_run: bool) -> dict:
    canonical, *dupes = members
    overrides_total = 0
    for d in dupes:
        overrides_total += _realocate_overrides(session, d.id, canonical.id, dry_run)
        if not dry_run:
            session.delete(d)
    return {
        "canonical_id": canonical.id,
        "dupes_dropped": [d.id for d in dupes],
        "overrides_realocados": overrides_total,
    }


def _load_rows(session, workspace_id: str) -> list:
    from sqlalchemy import select

    from backend.app.models import PropertyIdentity

    return list(
        session.execute(
            select(PropertyIdentity)
            .where(PropertyIdentity.workspace_id == workspace_id)
            .order_by(PropertyIdentity.created_at.asc())
        ).scalars()
    )


def _build_report(session, workspace_id: str, dry_run: bool) -> list:
    groups = _group_by_canonical(_load_rows(session, workspace_id))
    report = []
    for key, members in groups.items():
        if len(members) <= 1:
            continue
        merged = _merge_group(session, members, dry_run)
        merged["codigo_rfb"], merged["endereco_canonical"] = key
        report.append(merged)
    return report


def _process(workspace_id: str, dry_run: bool) -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.environ.get(
        "MATHOMS_DATABASE_URL_SYNC",
        "sqlite:////Users/davidrobert/Desktop/_dev/mathoms.ai/mathoms.db",
    )
    Session = sessionmaker(bind=create_engine(db_url, future=True), future=True)
    with Session() as session:
        report = _build_report(session, workspace_id, dry_run)
        if not dry_run:
            session.commit()
        return {
            "workspace_id": workspace_id,
            "dry_run": dry_run,
            "groups_merged": len(report),
            "details": report,
        }


def main() -> int:
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_id")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = _process(args.workspace_id, dry_run=not args.apply)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
