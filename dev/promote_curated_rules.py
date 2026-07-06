#!/usr/bin/env python3
"""Promove o ruleset curado A28.l5 (``curated_rules.py``) num workspace via learning loop.

Uso (na raiz do repo, com .env carregável e DB local):

    python3 dev/promote_curated_rules.py --workspace <workspace_id>            # dry-run
    python3 dev/promote_curated_rules.py --workspace <workspace_id> --apply   # cria regras

Dry-run lista matches estimados por keyword sem persistir nada. ``--apply``
cria ``categorization_rules`` + apply retroativo respeitando os invariantes
do loop (override manual sticky, mês fechado imutável, transferências
internas excluídas — ADR-186/188). Idempotente: regra existente = skip.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _resolve_detector(workspace_id: str, db):
    from backend.app.repositories.config_blob_repository import ConfigBlobRepository
    from backend.app.services.config_defaults import ConfigDefaultsLoader
    from backend.app.services.transfer_detector_resolver import (
        resolve_internal_transfer_detector,
    )

    repo = ConfigBlobRepository(db)
    defaults = ConfigDefaultsLoader()
    try:
        return asyncio.run(
            resolve_internal_transfer_detector(workspace_id, repo=repo, defaults=defaults)
        )
    except Exception as exc:  # noqa: BLE001 — fallback deliberado (paridade Celery task)
        print(f"  aviso: detector fallback vazio ({exc})")
        from backend.app.application.categorization.rule_preview_service import (
            empty_detector,
        )

        return empty_detector()


def _dry_run(rules, transactions) -> None:
    from backend.app.application.categorization.rule_management_service import (
        estimate_apply_matches,
    )

    print(f"{'keyword':<26} {'target':<20} {'matches':>8}")
    for rule in rules:
        estimated = estimate_apply_matches(
            keyword=rule.keyword,
            target_category=rule.target_category,
            transactions=transactions,
        )
        print(f"{rule.keyword:<26} {rule.target_category:<20} {estimated:>8}")
    print("\ndry-run: nada persistido. Use --apply para criar as regras.")


def _print_results(results) -> None:
    print(f"{'keyword':<26} {'target':<20} {'status':<16} {'applied':>8}")
    for r in results:
        print(f"{r.keyword:<26} {r.target_category:<20} {r.status:<16} {r.applied_count:>8}")
    created = sum(1 for r in results if r.status == "created")
    print(f"\n{created} regras criadas, {len(results) - created} skipadas.")
    print("Re-rode o pipeline (E4+) para refletir as regras no relatório.")


def _apply(workspace_id: str, transactions) -> None:
    from sqlalchemy import select

    from backend.app.application.categorization.curated_rules import (
        promote_curated_rules,
    )
    from backend.app.core.database import SyncSessionLocal
    from backend.app.models.workspace import Workspace

    with SyncSessionLocal() as db:
        workspace = db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        ).scalar_one_or_none()
        if workspace is None:
            sys.exit(f"workspace não encontrado: {workspace_id}")
        detector = _resolve_detector(workspace_id, db)
        results = promote_curated_rules(
            workspace=workspace, detector=detector, transactions=transactions, db=db
        )
    _print_results(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="workspace_id alvo")
    parser.add_argument(
        "--apply", action="store_true", help="persiste as regras (default: dry-run)"
    )
    args = parser.parse_args()

    from backend.app.application.categorization.curated_rules import (
        CURATED_RULES_A28_L5,
    )
    from backend.app.core.config import settings
    from backend.app.services.transaction_service import load_transactions

    transactions = load_transactions(args.workspace, str(settings.STORAGE_ROOT / args.workspace))
    print(f"{len(transactions)} transações carregadas do workspace {args.workspace}\n")
    if args.apply:
        _apply(args.workspace, transactions)
    else:
        _dry_run(CURATED_RULES_A28_L5, transactions)


if __name__ == "__main__":
    main()
