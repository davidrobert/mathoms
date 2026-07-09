#!/usr/bin/env python3
"""Backfill one-shot da supersessão de PropertyIdentity órfãs (ADR-324).

Re-roda ``resolve_dedup_winner_by_property_id`` sobre as rows do DB (valores
do baseline consolidado mais recente elegem o vencedor — nunca deriva o
mapping do artifact, só os valores) e aplica via o MESMO
``reconcile_supersession`` do forward-path. Dry-run por default; ``--apply``
executa. Idempotente: 2ª execução com ``--apply`` = zero mudanças.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MATHOMS_FERNET_KEY", "gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0=")
os.environ.setdefault("MATHOMS_JWT_SECRET", "x" * 32)


def _load_identities(session, workspace_id: str):
    from sqlalchemy import select

    from backend.app.models import PropertyIdentity

    stmt = (
        select(PropertyIdentity)
        .where(PropertyIdentity.workspace_id == workspace_id)
        .order_by(PropertyIdentity.created_at.asc())
    )
    return list(session.execute(stmt).scalars().all())


def _load_latest_baseline(session, workspace_id: str) -> dict | None:
    from sqlalchemy import select

    from backend.app.models.pipeline_artifact import PipelineArtifact
    from pipeline.artifact_store import stage_aliases

    candidates = set(stage_aliases("consolidate_baseline")) | {"E1.5c", "consolidate_baseline"}
    stmt = (
        select(PipelineArtifact.content_json)
        .where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage.in_(sorted(candidates)),
            PipelineArtifact.artifact_key == "baseline_patrimonial",
        )
        .order_by(PipelineArtifact.created_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _synthetic_entries(identities, baseline_payload: dict | None) -> list[dict]:
    """Espelha `real_estate_e5_integration._dedup_entries` — mesma eleição do forward-path."""
    valores = {
        im.get("property_id"): im.get("valores_31_12") or {}
        for im in (baseline_payload or {}).get("imoveis_consolidados") or []
    }
    return [
        {
            "property_id": ident.id,
            "codigo_rfb": ident.codigo_rfb,
            "endereco_canonical": ident.endereco_canonical,
            "descricao": ident.descricao_sample,
            "valores_31_12": valores.get(ident.id, {}),
        }
        for ident in identities
    ]


def _plan(identities, winner_by_pid: dict[str, str]) -> dict:
    known = {ident.id for ident in identities}
    losers = {
        pid: winner
        for pid, winner in winner_by_pid.items()
        if pid != winner and pid in known and winner in known
    }
    already = {ident.id for ident in identities if ident.superseded_at is not None}
    return {
        "rows": len(identities),
        "losers": losers,
        "to_supersede": sorted(set(losers) - already),
        "to_clear": sorted(already - set(losers)),
    }


def _session_factory():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    default_db = REPO_ROOT / "mathoms.db"
    db_url = os.environ.get("MATHOMS_DATABASE_URL_SYNC", f"sqlite:///{default_db}")
    return sessionmaker(bind=create_engine(db_url, future=True), future=True)


def _apply(session, workspace_id: str, winner_by_pid: dict[str, str]) -> dict:
    from backend.app.services.db_property_supersession_writer import (
        DBPropertySupersessionWriter,
    )

    outcome = DBPropertySupersessionWriter(session).reconcile_supersession(
        workspace_id, winner_by_pid
    )
    return {
        "superseded": outcome.superseded,
        "cleared": outcome.cleared,
        "overrides_repointed": outcome.overrides_repointed,
        "overrides_merged": outcome.overrides_merged,
    }


def _winner_map(identities, baseline: dict | None) -> dict[str, str]:
    from pipeline.domain.services.imoveis_dedup import (
        resolve_dedup_winner_by_property_id,
    )

    if baseline is None:
        print("[WARN] baseline ausente — eleição degrada determinística", file=sys.stderr)
    return resolve_dedup_winner_by_property_id(_synthetic_entries(identities, baseline))


def _process(workspace_id: str, dry_run: bool) -> dict:
    with _session_factory()() as session:
        identities = _load_identities(session, workspace_id)
        baseline = _load_latest_baseline(session, workspace_id)
        winner_by_pid = _winner_map(identities, baseline)
        report = {
            "workspace_id": workspace_id,
            "dry_run": dry_run,
            "baseline_found": baseline is not None,
            **_plan(identities, winner_by_pid),
        }
        if not dry_run:
            report["applied"] = _apply(session, workspace_id, winner_by_pid)
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_id")
    parser.add_argument("--apply", action="store_true", help="executa (default: dry-run)")
    args = parser.parse_args()
    report = _process(args.workspace_id, dry_run=not args.apply)
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
