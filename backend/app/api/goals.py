"""Goals API — F8.1 (ADR-073).

Primeiro endpoint escrito no padrão F8+:
- Prefix `/api/workspaces/{workspace_id}/...`
- Depende de `get_current_workspace` (não `get_current_user` + resolução legada)
- Services recebem `workspace_id` como primeiro argumento

Escopo em F8.1: apenas o tipo `INDEPENDENCIA_FINANCEIRA`. Outros tipos
serão adicionados em F8.5 conforme migrados do `goals.json`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.goal import (
    IFGoalComputeRequest,
    IFGoalComputeResponse,
    IFGoalHistoryResponse,
    IFGoalResponse,
    IFGoalUpsertRequest,
)
from backend.app.schemas.task import (
    TaskFilters,
    TaskListResponse,
    TaskResponse,
)
from backend.app.services import goal_service, task_service

router = APIRouter(
    prefix="/workspaces/{workspace_id}/goals",
    tags=["goals"],
)


@router.post(
    "/if/compute",
    response_model=IFGoalComputeResponse,
    summary="Dry-run: calcula derivados sem persistir",
)
async def compute_if_goal(
    body: IFGoalComputeRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
):
    """Preview live do frontend. Não toca o banco.

    Se `patrimonio_atual_brl` for enviado, inclui `percentual_conquistado`
    e `faltante_brl` para UI de progresso.
    """
    derived = goal_service.compute_if_derived(
        body.inputs, body.patrimonio_atual_brl
    )

    pct = None
    falt = None
    if body.patrimonio_atual_brl is not None and derived.if_meta_brl > 0:
        pct = round(
            100.0 * body.patrimonio_atual_brl / derived.if_meta_brl, 2
        )
        falt = round(
            max(0.0, derived.if_meta_brl - body.patrimonio_atual_brl), 2
        )

    return IFGoalComputeResponse(
        derived=derived,
        percentual_conquistado=pct,
        faltante_brl=falt,
    )


async def _enrich_if_goal_with_latest_patrimonio(
    response: IFGoalResponse,
    workspace_id: str,
    *,
    db: AsyncSession,
) -> IFGoalResponse:
    pat = await goal_service.get_latest_report_patrimonio_liquido(
        workspace_id, db=db
    )
    return response.model_copy(
        update={
            "derived": goal_service.compute_if_derived(response.inputs, pat),
        }
    )


@router.get(
    "/if",
    response_model=IFGoalResponse,
    summary="Retorna a meta IF vigente do workspace",
)
async def get_if_goal(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """404 se workspace ainda não tem meta IF persistida
    (frontend deve mostrar wizard nesse caso)."""
    response = await goal_service.get_current_goal_with_author(
        workspace.id, "INDEPENDENCIA_FINANCEIRA", db=db
    )
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace ainda não tem meta IF configurada",
        )
    return await _enrich_if_goal_with_latest_patrimonio(
        response, workspace.id, db=db
    )


@router.get(
    "/if/history",
    response_model=IFGoalHistoryResponse,
    summary="Histórico completo de versões da meta IF",
)
async def get_if_goal_history(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    responses = await goal_service.get_goal_history_with_authors(
        workspace.id, "INDEPENDENCIA_FINANCEIRA", db=db
    )
    return IFGoalHistoryResponse(goals=responses, total=len(responses))


@router.get(
    "/{goal_id}/tasks",
    response_model=TaskListResponse,
    summary="Tarefas vinculadas a esta meta",
)
async def list_tasks_for_goal(
    goal_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    include_done: bool = False,
):
    """Lista tasks com `related_goal_id == goal_id` dentro do workspace.

    Útil para a view `/plano/meta-if`: seção "Tarefas que destravam esta
    meta" com % completude.
    """
    filters = TaskFilters(related_goal_id=goal_id, include_done=include_done)
    tasks = await task_service.list_tasks(workspace.id, filters, db=db)
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
    )


@router.put(
    "/if",
    response_model=IFGoalResponse,
    status_code=status.HTTP_200_OK,
    summary="Cria nova versão da meta IF (fecha a anterior)",
    dependencies=[Depends(require_write_role)],
)
async def upsert_if_goal(
    body: IFGoalUpsertRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edição é append-only: cria novo registro com `effective_from = hoje`
    e fecha o anterior com `effective_to = ontem`. Histórico é preservado.

    RBAC (F9): `viewer` recebe 403 — apenas `owner` e `member` editam.
    """
    goal = await goal_service.create_if_goal_version(
        workspace.id,
        body.inputs,
        db=db,
        created_by=user.id,
        notes=body.notes,
    )
    await db.commit()
    await db.refresh(goal)
    base = goal_service._goal_to_response(goal, created_by_name=user.full_name)
    return await _enrich_if_goal_with_latest_patrimonio(
        base, workspace.id, db=db
    )
