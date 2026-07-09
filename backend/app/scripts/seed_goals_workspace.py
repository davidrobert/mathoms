"""Seed Goal types canônicos para um workspace específico (Sprint A10.7)."""

# Refactor de seed_goals_full_example.py (A10.7):
# - Sem hardcode `family_surname`; `--workspace-id` obrigatório.
# - Sem leitura de `_archive/.../goals.json`; fixtures declarativas inline.
# - Cria 4 Goal types canônicos (APORTE_MENSAL, INDEPENDENCIA_FINANCEIRA,
#   DOLARIZACAO, ALOCACAO_ALVO). PLANNING_CONTEXT não é mais populado —
#   A10.6/ADR-180 deletará a bag via `GoalsBundle`.
# - `--demo` carrega valores fictícios herdados do `goals.json` arquivado
#   em F8.4 para reproduzir ambiente de exemplo histórico.
# Uso: python -m backend.app.scripts.seed_goals_workspace
#      --workspace-id <UUID> [--dry-run|--apply] [--force-replace] [--demo]

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date

from sqlalchemy import select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.goal import Goal
from backend.app.models.workspace import Workspace
from backend.app.schemas.dto.goal import AlocacaoGoalInputsV2, meta_version_for_type
from backend.app.schemas.dto.goal.alocacao_shape_conversion import (
    compute_alocacao_derived_v2,
)
from backend.app.schemas.goal import IFGoalInputs
from backend.app.services.goal_service import (
    create_if_goal_version,
    get_current_goal,
)

logger = logging.getLogger("seed_goals_workspace")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ─────────────────────────────────────────────────────────────────────
# Fixtures default (workspace genérico) — números fictícios, ADR-090.
# ─────────────────────────────────────────────────────────────────────

_DEFAULT_IF_INPUTS = IFGoalInputs(
    renda_passiva_mensal_brl=10_000,
    trs_pct=4.0,
    retorno_real_anual_pct=5.0,
    horizonte_anos=15,
    taxa_retirada_conservadora_pct=4.0,
)

_DEFAULT_APORTE_PARAMS = {
    "meta_aporte_mensal_brl": 5_000,
    "dia_aporte": 5,
    "periodo_inicio": "Imediato",
    "distribuicao": {},
}

_DEFAULT_DOLARIZACAO_PARAMS = {
    "meta_usd": 10_000,
    "aporte_mensal_brl": 1_000,
}

_DEFAULT_ALOCACAO_PARAMS: dict = {
    # Alvo v2 (7 classes AUVP, ADR-141). Preset "Moderado" — consultor
    # refina via UI /plano/alocacao. Σ = 100.
    "rf_pos_pct": 20,
    "rf_pre_pct": 10,
    "rf_ipca_pct": 10,
    "acoes_br_pct": 20,
    "acoes_int_pct": 10,
    "fiis_pct": 15,
    "caixa_pct": 15,
    "rebalanceamento_modo": "por_aporte",
}


# ─────────────────────────────────────────────────────────────────────
# Fixtures de exemplo (modo --demo) — valores fictícios herdados
# do `goals.json` arquivado em F8.4 para reproduzir ambiente histórico.
# CLAUDE.md §Dados sensíveis — nada de CPF/valor real.
# ─────────────────────────────────────────────────────────────────────

_DEMO_IF_INPUTS = IFGoalInputs(
    renda_passiva_mensal_brl=20_000,
    trs_pct=5.0,
    retorno_real_anual_pct=6.0,
    horizonte_anos=15,
    taxa_retirada_conservadora_pct=4.0,
)

_DEMO_APORTE_PARAMS = {
    "meta_aporte_mensal_brl": 20_000,
    "dia_aporte": 5,
    "periodo_inicio": "Imediato",
    "distribuicao": {
        "renda_fixa": 8_000,
        "renda_variavel": 8_000,
        "alternativos": 4_000,
    },
}

_DEMO_DOLARIZACAO_PARAMS = {
    "meta_usd": 20_000,
    "aporte_mensal_brl": 2_000,
}

_DEMO_ALOCACAO_PARAMS: dict = {
    # Alvo v2 (7 classes AUVP) — preset "Agressivo" (equity-heavy). Σ = 100.
    "rf_pos_pct": 10,
    "rf_pre_pct": 5,
    "rf_ipca_pct": 10,
    "acoes_br_pct": 30,
    "acoes_int_pct": 15,
    "fiis_pct": 15,
    "caixa_pct": 15,
    "rebalanceamento_modo": "por_aporte",
}


async def _close_existing(existing: Goal, *, db) -> None:
    from datetime import timedelta

    existing.effective_to = date.today() - timedelta(days=1)
    db.add(existing)
    await db.flush()


def _build_goal(ws_id: str, goal_type: str, params: dict, notes: str) -> Goal:
    return Goal(
        workspace_id=ws_id,
        type=goal_type,
        params_json={"inputs": params, "meta_version": meta_version_for_type(goal_type)},
        derived_json=_seed_derived(goal_type, params),
        effective_from=date.today(),
        effective_to=None,
        notes=notes,
    )


def _seed_derived(goal_type: str, params: dict) -> dict:
    # Alocação v2 grava soma_percentuais no write-time (paridade com os
    # writers da API); demais tipos derivam on-read/no service.
    if goal_type == "ALOCACAO_ALVO":
        inputs = AlocacaoGoalInputsV2(**params)
        return compute_alocacao_derived_v2(inputs).model_dump(mode="json")
    return {}


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
    """Cria Goal se não existe. Retorna True se criou (ou criaria em dry-run)."""
    existing = await get_current_goal(ws_id, goal_type, db=db)
    if existing and not force:
        logger.info("  [skip] %s já existe (id=%s)", goal_type, existing.id[:8])
        return False
    if existing and force:
        await _close_existing(existing, db=db)
    if not apply:
        logger.info("  [dry-run] criaria %s", goal_type)
        return True
    goal = _build_goal(ws_id, goal_type, params, notes)
    db.add(goal)
    await db.flush()
    logger.info("  [ok] %s criado id=%s", goal_type, goal.id[:8])
    return True


async def _seed_if_goal(
    ws_id: str, inputs: IFGoalInputs, *, db, apply: bool, force: bool, notes: str
) -> bool:
    """Cria/recria INDEPENDENCIA_FINANCEIRA via service dedicado (paridade F8.1)."""
    existing = await get_current_goal(ws_id, "INDEPENDENCIA_FINANCEIRA", db=db)
    if existing and not force:
        logger.info("  [skip] INDEPENDENCIA_FINANCEIRA já existe")
        return False
    if force and existing:
        await _close_existing(existing, db=db)
    if apply:
        await create_if_goal_version(ws_id, inputs, db=db, notes=notes)
    logger.info("  [%s] INDEPENDENCIA_FINANCEIRA criada", "ok" if apply else "dry-run")
    return True


def _select_fixtures(demo: bool) -> tuple[IFGoalInputs, dict, dict, dict, str]:
    if demo:
        return (
            _DEMO_IF_INPUTS,
            _DEMO_APORTE_PARAMS,
            _DEMO_DOLARIZACAO_PARAMS,
            _DEMO_ALOCACAO_PARAMS,
            "Seed A10.7 (demo)",
        )
    return (
        _DEFAULT_IF_INPUTS,
        _DEFAULT_APORTE_PARAMS,
        _DEFAULT_DOLARIZACAO_PARAMS,
        _DEFAULT_ALOCACAO_PARAMS,
        "Seed A10.7",
    )


async def _seed_workspace(ws: Workspace, *, apply: bool, force: bool, demo: bool, db) -> int:
    if_inputs, aporte, dolar, aloc, notes_prefix = _select_fixtures(demo)
    logger.info("Processing %s (%s) — modo: %s", ws.id[:8], ws.name, "demo" if demo else "default")
    created = 0
    notes = lambda gt: f"{notes_prefix} — {gt}"  # noqa: E731
    if await _seed_if_goal(
        ws.id, if_inputs, db=db, apply=apply, force=force, notes=notes("INDEPENDENCIA_FINANCEIRA")
    ):
        created += 1
    for goal_type, params in (
        ("APORTE_MENSAL", aporte),
        ("DOLARIZACAO", dolar),
        ("ALOCACAO_ALVO", aloc),
    ):
        if await _create_goal_if_missing(
            ws.id, goal_type, params, db=db, apply=apply, force=force, notes=notes(goal_type)
        ):
            created += 1
    return created


async def _commit_or_log(*, apply: bool, db) -> None:
    if apply:
        await db.commit()
        logger.info("Seed aplicado com sucesso.")
    else:
        logger.info("[dry-run] nada persistido. Use --apply.")


async def seed(*, apply: bool, workspace_id: str, force_replace: bool, demo: bool) -> int:
    async with AsyncSessionLocal() as db:
        ws = (
            await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        ).scalar_one_or_none()
        if ws is None:
            logger.error("Workspace não encontrada: %s", workspace_id)
            return 2
        created = await _seed_workspace(ws, apply=apply, force=force_replace, demo=demo, db=db)
        verb = "criados" if apply else "(dry-run)"
        logger.info("  → %d Goal types %s para workspace %s", created, verb, ws.id[:8])
        await _commit_or_log(apply=apply, db=db)
    return 0


_DEMO_HELP = (
    "Usa fixtures de exemplo (valores históricos do goals.json "
    "arquivado em F8.4). Não usar em produção."
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dry-run", action="store_true")
    grp.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--workspace-id", required=True, help="UUID do workspace alvo (obrigatório)."
    )
    parser.add_argument(
        "--force-replace", action="store_true", help="Fecha vigente e cria nova versão."
    )
    parser.add_argument("--demo", action="store_true", help=_DEMO_HELP)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return asyncio.run(
        seed(
            apply=args.apply,
            workspace_id=args.workspace_id,
            force_replace=args.force_replace,
            demo=args.demo,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
