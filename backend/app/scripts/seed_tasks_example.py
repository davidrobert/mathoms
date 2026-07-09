"""Seed one-shot: importa `config/tarefas.md` para a workspace de exemplo
como entities `Task` no DB (ADR-074 §"Migração").

Preserva:
- `#number` histórico (1..43 + 2, 12 concluídas)
- priority (S/R/O)
- status (pendente→pending, feito→done)
- deadline (HARD_DATE se DD/MM/YYYY, MONTH se Abr/2026, etc.)
- ref (D01, goals.json, etc.)
- dependências (segundo-passo: inferência de `parent_task_id`)

Uso:
    python -m backend.app.scripts.seed_tasks_example --dry-run
    python -m backend.app.scripts.seed_tasks_example --apply

Idempotente: se workspace já tem tasks, pula (unless --force-replace).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.task import Task
from backend.app.models.workspace import Workspace
from backend.app.services.tarefas_md_parser import parse_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TAREFAS_MD_PATH = REPO_ROOT / "config" / "tarefas.md"
FAMILY_SURNAME_MATCH = "Example"

logger = logging.getLogger("seed_tasks_example")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def seed(
    *,
    apply: bool,
    workspace_id: str | None,
    force_replace: bool,
) -> int:
    if not TAREFAS_MD_PATH.exists():
        logger.error("Não encontrei %s", TAREFAS_MD_PATH)
        return 1

    parsed = parse_file(TAREFAS_MD_PATH)
    logger.info(
        "Parseadas %d tarefas do tarefas.md (#%s..#%s)",
        len(parsed),
        parsed[0].number if parsed else "?",
        parsed[-1].number if parsed else "?",
    )

    async with AsyncSessionLocal() as db:
        # Descobre workspace(s) alvo
        if workspace_id:
            # tenancy: global — seed CLI
            stmt = select(Workspace).where(Workspace.id == workspace_id)
        else:
            # tenancy: global — seed CLI
            stmt = select(Workspace).where(Workspace.family_surname == FAMILY_SURNAME_MATCH)
        result = await db.execute(stmt)
        workspaces = list(result.scalars().all())

        if not workspaces:
            logger.warning(
                "Nenhuma workspace encontrada (id=%s, family_surname=%s).",
                workspace_id,
                FAMILY_SURNAME_MATCH,
            )
            return 2

        processed = skipped = 0
        for ws in workspaces:
            existing_stmt = select(Task).where(Task.workspace_id == ws.id)
            existing = list((await db.execute(existing_stmt)).scalars().all())

            if existing and not force_replace:
                logger.info(
                    "[skip] workspace %s já tem %d tasks. " "Use --force-replace para recriar.",
                    ws.id,
                    len(existing),
                )
                skipped += 1
                continue

            if existing and force_replace:
                # Cascades nos attachments e suggestions.approved_task via FK
                for t in existing:
                    await db.delete(t)
                await db.flush()
                logger.info(
                    "[force] workspace %s: removidas %d tasks antigas",
                    ws.id,
                    len(existing),
                )

            if not apply:
                logger.info(
                    "[dry-run] criaria %d tasks para workspace %s",
                    len(parsed),
                    ws.id,
                )
                processed += 1
                continue

            # Primeira passe: cria todas as tasks sem parent_task_id
            number_to_id: dict[int, str] = {}
            for p in parsed:
                task = Task(
                    workspace_id=ws.id,
                    number=p.number,
                    title=p.title,
                    category=p.category,
                    priority=p.priority,
                    status=p.status,
                    deadline_kind=p.deadline_kind,
                    deadline_date=p.deadline_date,
                    deadline_label=p.deadline_label,
                    ref=p.ref,
                    status_reason=p.completion_detail if p.status == "done" else None,
                    created_from="seed",
                )
                db.add(task)
                await db.flush()
                number_to_id[p.number] = task.id

            # Segunda passe: resolve dependências
            deps_resolved = 0
            for p in parsed:
                if p.parent_number and p.parent_number in number_to_id:
                    task_stmt = select(Task).where(Task.id == number_to_id[p.number])
                    task = (await db.execute(task_stmt)).scalar_one()
                    task.parent_task_id = number_to_id[p.parent_number]
                    db.add(task)
                    deps_resolved += 1

            logger.info(
                "[ok] workspace %s: criadas %d tasks, %d dependências inferidas",
                ws.id,
                len(parsed),
                deps_resolved,
            )
            processed += 1

        if apply:
            await db.commit()
            logger.info(
                "Seed aplicado. Processados=%d, Skipped=%d.",
                processed,
                skipped,
            )
        else:
            logger.info(
                "[dry-run] nada persistido. Processáveis=%d, Skipped=%d. " "Use --apply.",
                processed,
                skipped,
            )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dry-run", action="store_true")
    grp.add_argument("--apply", action="store_true")
    parser.add_argument("--workspace-id", default=None)
    parser.add_argument(
        "--force-replace",
        action="store_true",
        help="Apaga tasks existentes antes de recriar. USE COM CUIDADO.",
    )
    args = parser.parse_args()
    return asyncio.run(
        seed(
            apply=args.apply,
            workspace_id=args.workspace_id,
            force_replace=args.force_replace,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
