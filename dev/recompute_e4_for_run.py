#!/usr/bin/env python3
"""Recomputa artefatos E4 de um pipeline_run a partir do E3 existente (ADR-255)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _connect(db_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    if db_url.startswith("sqlite+aiosqlite:"):
        db_url = db_url.replace("sqlite+aiosqlite:", "sqlite:", 1)
    engine = create_engine(db_url)
    return sessionmaker(bind=engine)()


def _load_configs(session, workspace_id: str) -> tuple[dict, dict]:
    """Best-effort: categorization + family_members do workspace; defaults se falhar."""
    try:
        from backend.app.services.db_config_store import DBConfigStore

        cs = DBConfigStore(session=session)
        cat_cfg = cs.get_categorization(workspace_id)
        fam_cfg = cs.get_family_members(workspace_id)
        cat_dict = _config_to_dict(cat_cfg) if cat_cfg else {}
        fam_dict = _config_to_dict(fam_cfg) if fam_cfg else {}
        return cat_dict, fam_dict
    except Exception as exc:  # noqa: BLE001
        print(f"  ! config load fail ({exc}); using defaults", file=sys.stderr)
        return {}, {}


def _config_to_dict(cfg) -> dict:
    """Serializa value object para dict (interface de from_configs)."""
    if hasattr(cfg, "to_dict"):
        return cfg.to_dict()
    if hasattr(cfg, "__dict__"):
        return cfg.__dict__
    return dict(cfg) if isinstance(cfg, dict) else {}


def _build_adapter(session, workspace_id: str):
    from pipeline.domain.services.e4_categorizer_adapter import E4CategorizerAdapter

    cat_dict, fam_dict = _load_configs(session, workspace_id)
    return E4CategorizerAdapter.from_configs(categorization=cat_dict, family=fam_dict)


def _persist_artifacts(store, payloads: dict) -> None:
    for key, payload in payloads.items():
        store.write("E4", key, payload)


def _summary(result, *, workspace_id: str, run_id: str, written: list, dry_run: bool) -> dict:
    report = result.cash_flow.dedup_report
    return {
        "workspace_id": workspace_id,
        "run_id": run_id,
        "receitas_total": result.cash_flow.receitas.total_transacoes,
        "despesas_total": result.cash_flow.despesas.total_transacoes,
        "transferencias_total": result.cash_flow.transferencias_count,
        "dups_collapsed": report.collapsed_count,
        "dups_review": report.review_count,
        "artifacts_written": written if not dry_run else [],
        "dry_run": dry_run,
    }


def recompute(session, *, workspace_id: str, run_id: str, dry_run: bool) -> dict:
    """Roda E4CategorizerAdapter no run + regrava artefatos E4."""
    from backend.app.services.db_artifact_store import DBArtifactStore
    from pipeline.domain.services.e4_serialization import serialize_e4_artifacts

    store = DBArtifactStore(session=session, workspace_id=workspace_id, pipeline_run_id=run_id)
    result = _build_adapter(session, workspace_id).categorize_via_store(store)
    payloads = serialize_e4_artifacts(result)
    if not dry_run:
        _persist_artifacts(store, payloads)
        session.commit()
    return _summary(
        result,
        workspace_id=workspace_id,
        run_id=run_id,
        written=list(payloads.keys()),
        dry_run=dry_run,
    )


def _parse_argv(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db-url", default=os.environ.get("MATHOMS_DATABASE_URL", ""))
    parser.add_argument("--apply", action="store_true", help="sem essa flag, dry-run")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import json

    args = _parse_argv(argv)
    if not args.db_url:
        print("error: --db-url ou MATHOMS_DATABASE_URL obrigatório", file=sys.stderr)
        return 2
    session = _connect(args.db_url)
    try:
        summary = recompute(
            session,
            workspace_id=args.workspace_id,
            run_id=args.run_id,
            dry_run=not args.apply,
        )
    finally:
        session.close()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
