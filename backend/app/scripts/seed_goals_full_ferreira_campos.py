"""Seed completo: migra TODAS as seções do goals.json para Goal entities
no DB (ADR-075 §F8.4 — cutover final).

Execução:
    python -m backend.app.scripts.seed_goals_full_ferreira_campos --dry-run
    python -m backend.app.scripts.seed_goals_full_ferreira_campos --apply

Idempotente: pula types que já existem no workspace (--force-replace
para recriar).

Estratégia de migração por tipo:
- INDEPENDENCIA_FINANCEIRA → seed já criado em F8.1 (pula se existir)
- APORTE_MENSAL → seção `aportes` do goals.json
- DOLARIZACAO → seção `dolarizacao`
- ALOCACAO_ALVO → seção `alocacao_alvo`
- PLANNING_CONTEXT → TODAS as demais seções como blob JSON genérico
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.goal import VALID_GOAL_TYPES, Goal
from backend.app.models.workspace import Workspace
from backend.app.schemas.goal import IFGoalInputs
from backend.app.services.goal_service import (
    compute_if_derived,
    create_if_goal_version,
    get_current_goal,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GOALS_JSON_PATH = REPO_ROOT / "config" / "goals.json"
FAMILY_SURNAME_MATCH = "Ferreira Campos"

logger = logging.getLogger("seed_goals_full")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# Seções que viram Goal types dedicados (já mapeadas no adapter)
_DEDICATED_SECTIONS = {
    "independencia_financeira",
    "aportes",
    "dolarizacao",
    "alocacao_alvo",
}

# Seções internas / metadados — NÃO migrar (ficam no _comment/meta do JSON)
_SKIP_SECTIONS = {
    "_comment",
    "_ultima_atualizacao",
    "_fonte",
    # NB: `dashboard` foi inicialmente classificado como config operacional,
    # mas E6 lê `GOALS_CONFIG.get("dashboard", {})` — precisa estar no
    # adapter output. Vai para PLANNING_CONTEXT.
}


async def _create_goal_if_missing(
    ws_id: str,
    goal_type: str,
    params: dict,
    *,
    db,
    apply: bool,
    force: bool,
    notes: str,
) -> bool:
    """Cria Goal se não existe. Retorna True se criou."""
    existing = await get_current_goal(ws_id, goal_type, db=db)
    if existing and not force:
        logger.info("  [skip] %s já existe (id=%s)", goal_type, existing.id[:8])
        return False
    if existing and force:
        from datetime import timedelta

        existing.effective_to = date.today() - timedelta(days=1)
        db.add(existing)
        await db.flush()

    if not apply:
        logger.info("  [dry-run] criaria %s", goal_type)
        return True

    goal = Goal(
        workspace_id=ws_id,
        type=goal_type,
        params_json={"inputs": params, "meta_version": 1},
        derived_json={},  # derivados são opcionais para types não-IF
        effective_from=date.today(),
        effective_to=None,
        notes=notes,
    )
    db.add(goal)
    await db.flush()
    logger.info("  [ok] %s criado id=%s", goal_type, goal.id[:8])
    return True


async def seed(
    *,
    apply: bool,
    workspace_id: str | None,
    force_replace: bool,
) -> int:
    if not GOALS_JSON_PATH.exists():
        logger.error("goals.json não encontrado: %s", GOALS_JSON_PATH)
        return 1

    goals_data = json.loads(GOALS_JSON_PATH.read_text(encoding="utf-8"))
    logger.info("Loaded goals.json (%d top-level keys)", len(goals_data))

    async with AsyncSessionLocal() as db:
        if workspace_id:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
        else:
            stmt = select(Workspace).where(Workspace.family_surname == FAMILY_SURNAME_MATCH)
        workspaces = list((await db.execute(stmt)).scalars().all())
        if not workspaces:
            logger.warning("Nenhuma workspace encontrada")
            return 2

        for ws in workspaces:
            logger.info("Processing workspace %s (%s)", ws.id[:8], ws.name)
            created = 0

            # -- IF (reusa seed existente se já presente) --
            if_section = goals_data.get("independencia_financeira", {})
            existing_if = await get_current_goal(ws.id, "INDEPENDENCIA_FINANCEIRA", db=db)
            if not existing_if:
                if if_section.get("renda_passiva_meta_mensal"):
                    inputs = IFGoalInputs(
                        renda_passiva_mensal_brl=if_section["renda_passiva_meta_mensal"],
                        trs_pct=if_section.get("trs_pct", 5.0),
                        retorno_real_anual_pct=if_section.get("retorno_real_anual_pct", 6.0),
                        horizonte_anos=15,
                        taxa_retirada_conservadora_pct=if_section.get(
                            "taxa_retirada_segura_classica_pct", 4.0
                        ),
                    )
                    if apply:
                        await create_if_goal_version(
                            ws.id,
                            inputs,
                            db=db,
                            notes="Seed full F8.4 — from goals.json",
                        )
                    logger.info("  [ok] INDEPENDENCIA_FINANCEIRA criada")
                    created += 1
            else:
                logger.info("  [skip] INDEPENDENCIA_FINANCEIRA já existe")

            # -- APORTE_MENSAL --
            aportes = goals_data.get("aportes", {})
            if aportes:
                params = {
                    "meta_aporte_mensal_brl": aportes.get("meta_aporte_mensal", 20000),
                    "dia_aporte": aportes.get("dia_aporte", 5),
                    "periodo_inicio": aportes.get("periodo_inicio", "Imediato"),
                    "distribuicao": aportes.get("distribuicao", {}),
                }
                if await _create_goal_if_missing(
                    ws.id,
                    "APORTE_MENSAL",
                    params,
                    db=db,
                    apply=apply,
                    force=force_replace,
                    notes="Seed F8.4 — from goals.json:aportes",
                ):
                    created += 1

            # -- DOLARIZACAO --
            dolar = goals_data.get("dolarizacao", {})
            if dolar:
                params = {
                    "meta_usd": dolar.get("meta_usd", 20000),
                    "aporte_mensal_brl": dolar.get("aporte_mensal_brl", 2000),
                }
                if await _create_goal_if_missing(
                    ws.id,
                    "DOLARIZACAO",
                    params,
                    db=db,
                    apply=apply,
                    force=force_replace,
                    notes="Seed F8.4 — from goals.json:dolarizacao",
                ):
                    created += 1

            # -- ALOCACAO_ALVO --
            aloc = goals_data.get("alocacao_alvo", {})
            if aloc:
                params = dict(aloc)
                if await _create_goal_if_missing(
                    ws.id,
                    "ALOCACAO_ALVO",
                    params,
                    db=db,
                    apply=apply,
                    force=force_replace,
                    notes="Seed F8.4 — from goals.json:alocacao_alvo",
                ):
                    created += 1

            # -- PLANNING_CONTEXT (tudo que sobrou) --
            remaining: dict = {}
            for k, v in goals_data.items():
                if k in _DEDICATED_SECTIONS or k in _SKIP_SECTIONS:
                    continue
                remaining[k] = v

            if remaining:
                if await _create_goal_if_missing(
                    ws.id,
                    "PLANNING_CONTEXT",
                    remaining,
                    db=db,
                    apply=apply,
                    force=force_replace,
                    notes=(
                        f"Seed F8.4 — {len(remaining)} seções restantes "
                        f"de goals.json: {', '.join(sorted(remaining.keys())[:5])}..."
                    ),
                ):
                    created += 1

            logger.info(
                "  → %d Goal types %s para workspace %s",
                created,
                "criados" if apply else "(dry-run)",
                ws.id[:8],
            )

        if apply:
            await db.commit()
            logger.info("Seed aplicado com sucesso.")
        else:
            logger.info("[dry-run] nada persistido. Use --apply.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dry-run", action="store_true")
    grp.add_argument("--apply", action="store_true")
    parser.add_argument("--workspace-id", default=None)
    parser.add_argument("--force-replace", action="store_true")
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
