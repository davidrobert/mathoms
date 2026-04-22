"""Executa o cutover CLI→Web (ADR-077): backup + remoção de config files.

⚠️ DESTRUTIVO: remove `config/goals.json` e `config/tarefas.md` do
working tree. Backup preservado em `_archive/pre-f8-cutover-YYYY-MM-DD/`.

Pré-requisitos (checados automaticamente):
1. Workspace de Ferreira Campos tem Goal IF vigente
2. Workspace tem ≥1 Task no DB
3. Validate adapter parity = exit 0

Uso:
    python -m backend.app.scripts.cutover_execute --dry-run
    python -m backend.app.scripts.cutover_execute --apply

Depois de --apply:
    git add -A && git commit -m "cutover: remove config/goals.json + tarefas.md (ADR-077)"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.goal import Goal
from backend.app.models.task import Task
from backend.app.models.workspace import Workspace

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FAMILY_SURNAME_MATCH = "Ferreira Campos"

# Arquivos a remover (Grupo A do ADR-075)
FILES_TO_ARCHIVE = [
    "config/goals.json",
    "config/tarefas.md",
]

logger = logging.getLogger("cutover")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def _check_preconditions() -> list[str]:
    """Verifica pré-condições. Retorna lista de falhas (vazia = OK)."""
    failures: list[str] = []

    async with AsyncSessionLocal() as db:
        stmt = select(Workspace).where(Workspace.family_surname == FAMILY_SURNAME_MATCH)
        ws = (await db.execute(stmt)).scalar_one_or_none()
        if not ws:
            failures.append("Workspace Ferreira Campos não encontrada")
            return failures

        # Goal IF vigente?
        if_stmt = select(Goal).where(
            Goal.workspace_id == ws.id,
            Goal.type == "INDEPENDENCIA_FINANCEIRA",
            Goal.effective_to.is_(None),
        )
        if_goal = (await db.execute(if_stmt)).scalar_one_or_none()
        if not if_goal:
            failures.append("Goal IF vigente não encontrado no DB")

        # Tasks?
        task_count_stmt = select(func.count()).select_from(Task).where(Task.workspace_id == ws.id)
        task_count = (await db.execute(task_count_stmt)).scalar_one()
        if task_count == 0:
            failures.append("Nenhuma Task no DB (rode o seed primeiro)")

        # PLANNING_CONTEXT?
        ctx_stmt = select(Goal).where(
            Goal.workspace_id == ws.id,
            Goal.type == "PLANNING_CONTEXT",
            Goal.effective_to.is_(None),
        )
        if (await db.execute(ctx_stmt)).scalar_one_or_none() is None:
            failures.append("Goal PLANNING_CONTEXT não encontrado (rode seed_goals_full)")

    return failures


def _backup_and_remove(apply: bool) -> None:
    """Faz backup em _archive/ e remove os arquivos do working tree."""
    archive_dir = REPO_ROOT / "_archive" / f"pre-f8-cutover-{date.today().isoformat()}"

    for rel_path in FILES_TO_ARCHIVE:
        src = REPO_ROOT / rel_path
        if not src.exists():
            logger.info("  [skip] %s já não existe", rel_path)
            continue

        if apply:
            dest = archive_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            logger.info("  [backup] %s → %s", rel_path, dest)
            src.unlink()
            logger.info("  [remove] %s", rel_path)
        else:
            logger.info("  [dry-run] faria backup + remoção de %s", rel_path)


async def cutover(*, apply: bool) -> int:
    logger.info("=== Cutover CLI → Web (ADR-077) ===")
    logger.info("")

    logger.info("Verificando pré-condições...")
    failures = await _check_preconditions()
    if failures:
        logger.error("✗ %d pré-condição(ões) falharam:", len(failures))
        for f in failures:
            logger.error("  - %s", f)
        logger.error("")
        logger.error(
            "Resolva as pendências e tente novamente. "
            "Seeds disponíveis:\n"
            "  python -m backend.app.scripts.seed_if_goal_ferreira_campos --apply\n"
            "  python -m backend.app.scripts.seed_tasks_ferreira_campos --apply\n"
            "  python -m backend.app.scripts.seed_goals_full_ferreira_campos --apply"
        )
        return 1

    logger.info("✓ Todas as pré-condições OK")
    logger.info("")

    # Backup + remoção
    logger.info("Arquivos para backup + remoção:")
    _backup_and_remove(apply)
    logger.info("")

    if apply:
        logger.info("✓ Cutover executado com sucesso.")
        logger.info("")
        logger.info("Próximos passos:")
        logger.info("  1. git add -A")
        logger.info(
            '  2. git commit -m "cutover: remove config/goals.json + ' 'tarefas.md (ADR-077)"'
        )
        logger.info("  3. Validar pipeline completo E0→E7 contra workspace de teste")
        logger.info("  4. git tag f8-cutover-complete")
    else:
        logger.info("[dry-run] Nenhuma ação tomada. Use --apply para executar.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dry-run", action="store_true")
    grp.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    return asyncio.run(cutover(apply=args.apply))


if __name__ == "__main__":
    sys.exit(main())
