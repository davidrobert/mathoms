#!/usr/bin/env python3
"""Dedup property_identity rows por workspace — 3 passes idempotentes (ADR-215 + ADR-225 §3)."""

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

# Subcódigos específicos do Grupo 01 (Bens Imóveis) RFB.
# "01" e "" são genéricos (grupo-pai sem subcódigo).
_SPECIFIC_CODIGOS_RFB = frozenset({"11", "12", "13", "14", "15", "17", "19"})


def _group_by_canonical(rows) -> dict:
    """Passe 1: agrupa por (codigo_rfb, endereco_canonical) excluindo NULL."""
    groups: dict[tuple[str, str], list] = defaultdict(list)
    for r in rows:
        if r.endereco_canonical is None:
            continue
        groups[(r.codigo_rfb, r.endereco_canonical)].append(r)
    return groups


def _group_by_canonical_only(rows) -> dict:
    """Passe 3: agrupa por endereco_canonical ignorando codigo_rfb."""
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        if r.endereco_canonical is None:
            continue
        groups[r.endereco_canonical].append(r)
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


def _pass_0_recanonicalize(session, rows, dry_run: bool) -> list:
    """Passe 0 (ADR-225 §3): re-canonicaliza rows com endereco_canonical=NULL."""
    from pipeline.domain.services.endereco_canonicalizer import canonicalize

    updates = []
    for row in rows:
        if row.endereco_canonical is not None:
            continue
        new_canonical = canonicalize(row.descricao_sample or "")
        if new_canonical is None:
            continue
        if not dry_run:
            row.endereco_canonical = new_canonical
            row.low_confidence = False
        updates.append({"property_id": row.id, "new_canonical": new_canonical})
    return updates


def _pass_3_classify(members: list) -> tuple[bool, dict]:
    """Decide se grupo cross-codigo é fundível ou conflito humano."""
    codigos = {m.codigo_rfb for m in members}
    specifics = codigos & _SPECIFIC_CODIGOS_RFB
    if len(specifics) >= 2:
        return False, {
            "codigos_specificos_divergentes": sorted(specifics),
            "property_ids": [m.id for m in members],
        }
    return True, {"codigos_fundidos": sorted(codigos)}


def _pass_3_cross_codigo(session, rows, dry_run: bool) -> tuple[list, list]:
    """Passe 3: funde rows cross-codigo_rfb quando 1 lado é genérico."""
    merged: list = []
    conflicts: list = []
    for canonical_key, members in _group_by_canonical_only(rows).items():
        if len({m.codigo_rfb for m in members}) <= 1:
            continue
        mergeable, info = _pass_3_classify(members)
        info["endereco_canonical"] = canonical_key
        if not mergeable:
            conflicts.append(info)
            continue
        members_sorted = sorted(
            members, key=lambda m: (m.codigo_rfb not in _SPECIFIC_CODIGOS_RFB, m.created_at)
        )
        merged.append({**_merge_group(session, members_sorted, dry_run), **info})
    return merged, conflicts


def _pass_1_strict(session, rows, dry_run: bool) -> list:
    """Passe 1: dedup estrito por (codigo_rfb, endereco_canonical)."""
    merged: list = []
    for key, members in _group_by_canonical(rows).items():
        if len(members) <= 1:
            continue
        m = _merge_group(session, members, dry_run)
        m["codigo_rfb"], m["endereco_canonical"] = key
        merged.append(m)
    return merged


def _build_report(session, workspace_id: str, dry_run: bool) -> dict:
    rows = _load_rows(session, workspace_id)
    pass_0 = _pass_0_recanonicalize(session, rows, dry_run)
    # Re-load para refletir updates do passe 0 quando não dry-run.
    if not dry_run and pass_0:
        rows = _load_rows(session, workspace_id)
    pass_1 = _pass_1_strict(session, rows, dry_run)
    if not dry_run and pass_1:
        rows = _load_rows(session, workspace_id)
    pass_3, conflicts = _pass_3_cross_codigo(session, rows, dry_run)
    return {
        "pass_0_recanonicalized": pass_0,
        "pass_1_strict_merged": pass_1,
        "pass_3_cross_codigo_merged": pass_3,
        "pass_3_conflicts_need_human": conflicts,
    }


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
            **report,
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
