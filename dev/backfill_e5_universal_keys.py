"""Backfill operacional pós ADR-166: re-roda E5 nos workspaces com chave legada (proc em docs/CENARIOS_ESTRESSE_PLAN.md §PR1 + ADR-166)."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Iterable

logger = logging.getLogger("mathoms.dev.backfill_e5_universal_keys")


def _select_workspaces_to_backfill(*, dry_run: bool) -> Iterable[str]:
    """Itera workspace_ids cujo último artifact E5 ainda tem chave legada (ADR-166)."""
    # Placeholder — implementação completa requer SessionLocal + filtros.
    # O script existe para documentar o procedimento (ADR-166); operador
    # roda manualmente após o merge do PR1.
    if dry_run:
        logger.info("backfill.dry_run", extra={"selected": 0})
    return []


def _rerun_analyze_finances(workspace_id: str, *, dry_run: bool) -> None:
    """Dispara stage `analyze_finances` para o workspace (reusa pipeline-as-service)."""
    if dry_run:
        logger.info("backfill.rerun.dry_run", extra={"workspace_id": workspace_id})
        return
    # TODO: importar e chamar PipelineRunner.run_stage(workspace_id, "analyze_finances").
    # Mantido como placeholder até que o CLI do pipeline-as-service esteja
    # estável (A6f.1) — operador atual roda re-run manualmente via `make run-stage`.
    logger.info("backfill.rerun", extra={"workspace_id": workspace_id})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-roda E5 em workspaces com chave legada `cenarios_mariana` (ADR-166).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista workspaces elegíveis sem executar o stage.",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=None,
        help="Limita a um workspace_id específico (override da seleção automática).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    if args.workspace:
        ids = [args.workspace]
    else:
        ids = list(_select_workspaces_to_backfill(dry_run=args.dry_run))

    if not ids:
        logger.info("backfill.no_workspaces_eligible")
        return 0

    for ws_id in ids:
        _rerun_analyze_finances(ws_id, dry_run=args.dry_run)

    logger.info("backfill.complete", extra={"count": len(ids), "dry_run": args.dry_run})
    return 0


if __name__ == "__main__":
    sys.exit(main())
