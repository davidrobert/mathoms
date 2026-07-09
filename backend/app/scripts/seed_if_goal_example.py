"""Seed one-shot: cria Goal IF para workspace(s) selecionada(s) por family_surname.

ADR-073 §"Migração do `goals.json`" (one-shot F8.1; inputs de exemplo sintéticos).

Paridade com os inputs de exemplo abaixo:
    independencia_financeira.if_meta = 3000000.0

Calculado a partir de:
    renda_passiva_mensal_brl = 10000
    trs_pct = 4.0
    retorno_real_anual_pct = 6.0
    horizonte_anos = 15

Execução:
    # Dry-run (mostra o que faria)
    python -m backend.app.scripts.seed_if_goal_example --dry-run

    # Aplicar
    python -m backend.app.scripts.seed_if_goal_example --apply

    # Escolher workspace específica
    python -m backend.app.scripts.seed_if_goal_example --workspace-id <uuid> --apply

Idempotente: se o workspace JÁ tem Goal IF vigente, pula (não duplica).
Para recriar, use --force-replace (fecha o atual e cria novo).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date

from sqlalchemy import select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.workspace import Workspace
from backend.app.schemas.goal import IFGoalInputs
from backend.app.services.goal_service import (
    compute_if_derived,
    create_if_goal_version,
    get_current_goal,
)

logger = logging.getLogger("seed_if_goal_example")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# Inputs de exemplo sintéticos (números redondos; sem dado real de workspace)
EXAMPLE_IF_INPUTS = IFGoalInputs(
    renda_passiva_mensal_brl=10000,
    trs_pct=4.0,
    retorno_real_anual_pct=6.0,
    horizonte_anos=15,
    taxa_retirada_conservadora_pct=3.0,
)
EXPECTED_IF_META_BRL = 3_000_000.0
FAMILY_SURNAME_MATCH = "Example"


async def seed(
    *,
    apply: bool,
    workspace_id: str | None,
    force_replace: bool,
) -> int:
    """Retorna exit code (0 = ok, 1 = erro, 2 = nenhuma workspace encontrada)."""
    # Validação de paridade pré-execução
    derived = compute_if_derived(EXAMPLE_IF_INPUTS)
    if derived.if_meta_brl != EXPECTED_IF_META_BRL:
        logger.error(
            "Paridade quebrada: if_meta_brl=%s, esperado=%s. "
            "Revise compute_if_derived antes de aplicar.",
            derived.if_meta_brl,
            EXPECTED_IF_META_BRL,
        )
        return 1

    logger.info(
        "Valores derivados OK: if_meta=R$ %.2f, aporte_necessario=R$ %.2f/mês",
        derived.if_meta_brl,
        derived.aporte_necessario_mensal_brl,
    )

    async with AsyncSessionLocal() as db:
        # Descobre workspace(s)
        if workspace_id:
            # tenancy: global — seed CLI de uma workspace específica
            stmt = select(Workspace).where(Workspace.id == workspace_id)
        else:
            # tenancy: global — seed CLI: filtro por family_surname
            stmt = select(Workspace).where(Workspace.family_surname == FAMILY_SURNAME_MATCH)
        result = await db.execute(stmt)
        workspaces = list(result.scalars().all())

        if not workspaces:
            logger.warning(
                "Nenhuma workspace encontrada (id=%s, family_surname=%s). " "Nada a fazer.",
                workspace_id,
                FAMILY_SURNAME_MATCH,
            )
            return 2

        logger.info("Encontradas %d workspace(s) candidata(s):", len(workspaces))
        for ws in workspaces:
            logger.info("  - %s / %s (%s)", ws.id, ws.name, ws.family_surname)

        processed = 0
        skipped = 0
        for ws in workspaces:
            existing = await get_current_goal(ws.id, "INDEPENDENCIA_FINANCEIRA", db=db)
            if existing and not force_replace:
                logger.info(
                    "[skip] workspace %s já tem Goal IF vigente "
                    "(if_meta=R$ %.2f). Use --force-replace para substituir.",
                    ws.id,
                    existing.derived_json.get("if_meta_brl", 0),
                )
                skipped += 1
                continue

            if not apply:
                logger.info(
                    "[dry-run] criaria Goal IF para workspace %s " "(if_meta=R$ %.2f)",
                    ws.id,
                    derived.if_meta_brl,
                )
                processed += 1
                continue

            goal = await create_if_goal_version(
                ws.id,
                EXAMPLE_IF_INPUTS,
                db=db,
                created_by=None,  # seed CLI, sem user humano
                notes=(
                    "Seed one-shot F8.1 — valores derivados de "
                    "config/goals.json (independencia_financeira, 2026-04)"
                ),
                effective_from=date.today(),
            )
            logger.info(
                "[ok] workspace %s: Goal IF criado id=%s if_meta=R$ %.2f",
                ws.id,
                goal.id,
                goal.derived_json["if_meta_brl"],
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
                "[dry-run] nada foi persistido. " "Processáveis=%d, Skipped=%d. Use --apply.",
                processed,
                skipped,
            )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dry-run", action="store_true", help="Não persiste")
    grp.add_argument("--apply", action="store_true", help="Aplica no banco")
    parser.add_argument(
        "--workspace-id",
        type=str,
        default=None,
        help="UUID específico. Se omitido, busca por family_surname=" f"'{FAMILY_SURNAME_MATCH}'.",
    )
    parser.add_argument(
        "--force-replace",
        action="store_true",
        help="Fecha o Goal IF atual e cria novo (histórico preservado).",
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
