"""Goals API — router fino (A6e.4 · ADR-101 R15/R16 · ADR-073).

Endpoints sob ``/workspaces/{workspace_id}/goals/...`` delegam a use
cases em :mod:`backend.app.application.goal`. Erros de domínio traduzidos
para HTTP por handlers globais em ``main.py``.

4 tipos versionados append-only: IF, aportes, dolarização, alocação.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.goal import (
    compute_alocacao_projection,
    compute_aporte_projection,
    compute_dolar_projection,
    compute_if_projection,
    create_if_goal_version,
    create_typed_goal_version,
    get_active_if_goal,
    get_active_typed_goal,
    list_if_goal_versions,
    list_typed_goal_versions,
)
from backend.app.application.goal._author_enrichment import (
    attach_author_name,
    resolve_author_names,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.goal_repository import GoalRepository
from backend.app.schemas.dto.goal import (
    AlocacaoGoalComputeRequest,
    AlocacaoGoalComputeResponse,
    AlocacaoGoalHistoryResponse,
    AlocacaoGoalResponse,
    AlocacaoGoalUpsertCommand,
    AporteGoalComputeRequest,
    AporteGoalComputeResponse,
    AporteGoalHistoryResponse,
    AporteGoalResponse,
    AporteGoalUpsertCommand,
    DolarGoalComputeRequest,
    DolarGoalComputeResponse,
    DolarGoalHistoryResponse,
    DolarGoalResponse,
    DolarGoalUpsertCommand,
    IFGoalComputeRequest,
    IFGoalComputeResponse,
    IFGoalHistoryResponse,
    IFGoalResponse,
    IFGoalUpsertCommand,
)
from backend.app.schemas.task import TaskFilters, TaskListResponse, TaskResponse
from backend.app.services import task_service
from backend.app.services.goal_service import get_latest_report_patrimonio_liquido

router = APIRouter(prefix="/workspaces/{workspace_id}/goals", tags=["goals"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> GoalRepository:
    return GoalRepository(db)


async def _history_typed(
    goal_type: str, workspace_id: str, *, repo: GoalRepository, db: AsyncSession
) -> list[BaseModel]:
    goals = await repo.list_by_workspace_and_type(workspace_id, goal_type)
    names = await resolve_author_names(
        {g.created_by for g in goals if g.created_by}, db=db
    )
    return await list_typed_goal_versions(
        workspace_id, goal_type, repo=repo, author_names=names
    )


async def _read_typed(
    goal_type: str, workspace_id: str, *, repo: GoalRepository, db: AsyncSession
) -> BaseModel:
    resp = await get_active_typed_goal(workspace_id, goal_type, repo=repo)
    return await attach_author_name(resp, db=db)


async def _write_typed(
    goal_type: str, inputs: BaseModel, notes: Optional[str], *,
    workspace: Workspace, user: User, repo: GoalRepository, db: AsyncSession,
) -> BaseModel:
    resp = await create_typed_goal_version(
        goal_type, inputs, notes,
        workspace_id=workspace.id, created_by=user.id, repo=repo,
        created_by_name=user.full_name,
    )
    await db.commit()
    return resp


# INDEPENDENCIA_FINANCEIRA (F8.1) ════════════════════════════════════════


@router.post("/if/compute", response_model=IFGoalComputeResponse,
             summary="Dry-run: calcula derivados sem persistir")
async def compute_if_goal(
    body: IFGoalComputeRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
) -> IFGoalComputeResponse:
    return compute_if_projection(body)


@router.get("/if", response_model=IFGoalResponse,
            summary="Retorna a meta IF vigente do workspace")
async def get_if_goal(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> IFGoalResponse:
    patrimonio = await get_latest_report_patrimonio_liquido(workspace.id, db=db)
    resp = await get_active_if_goal(
        workspace.id, repo=repo, patrimonio_atual_brl=patrimonio
    )
    return await attach_author_name(resp, db=db)  # type: ignore[return-value]


@router.get("/if/history", response_model=IFGoalHistoryResponse,
            summary="Histórico completo de versões da meta IF")
async def get_if_goal_history(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> IFGoalHistoryResponse:
    goals = await repo.list_by_workspace_and_type(
        workspace.id, "INDEPENDENCIA_FINANCEIRA"
    )
    names = await resolve_author_names(
        {g.created_by for g in goals if g.created_by}, db=db
    )
    return await list_if_goal_versions(workspace.id, repo=repo, author_names=names)


@router.put("/if", response_model=IFGoalResponse,
            summary="Cria nova versão da meta IF (fecha a anterior)",
            dependencies=[Depends(require_write_role)])
async def upsert_if_goal(
    body: IFGoalUpsertCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> IFGoalResponse:
    patrimonio = await get_latest_report_patrimonio_liquido(workspace.id, db=db)
    resp = await create_if_goal_version(
        body, workspace_id=workspace.id, created_by=user.id, repo=repo,
        patrimonio_atual_brl=patrimonio, created_by_name=user.full_name,
    )
    await db.commit()
    return resp


# APORTE_MENSAL (F8.5) ═══════════════════════════════════════════════════


@router.post("/aportes/compute", response_model=AporteGoalComputeResponse,
             summary="Dry-run: calcula derivados de aportes")
async def compute_aporte_goal(
    body: AporteGoalComputeRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
) -> AporteGoalComputeResponse:
    return compute_aporte_projection(body)


@router.get("/aportes", response_model=AporteGoalResponse,
            summary="Meta de aportes vigente")
async def get_aporte_goal(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> AporteGoalResponse:
    return await _read_typed("APORTE_MENSAL", workspace.id, repo=repo, db=db)  # type: ignore[return-value]


@router.get("/aportes/history", response_model=AporteGoalHistoryResponse,
            summary="Histórico de versões da meta de aportes")
async def get_aporte_goal_history(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> AporteGoalHistoryResponse:
    responses = await _history_typed("APORTE_MENSAL", workspace.id, repo=repo, db=db)
    return AporteGoalHistoryResponse(goals=responses, total=len(responses))  # type: ignore[arg-type]


@router.put("/aportes", response_model=AporteGoalResponse,
            summary="Cria nova versão da meta de aportes",
            dependencies=[Depends(require_write_role)])
async def upsert_aporte_goal(
    body: AporteGoalUpsertCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> AporteGoalResponse:
    return await _write_typed(  # type: ignore[return-value]
        "APORTE_MENSAL", body.inputs, body.notes,
        workspace=workspace, user=user, repo=repo, db=db,
    )


# DOLARIZACAO (F8.5) ═════════════════════════════════════════════════════


@router.post("/dolarizacao/compute", response_model=DolarGoalComputeResponse,
             summary="Dry-run: calcula derivados de dolarização")
async def compute_dolar_goal(
    body: DolarGoalComputeRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
) -> DolarGoalComputeResponse:
    return compute_dolar_projection(body)


@router.get("/dolarizacao", response_model=DolarGoalResponse,
            summary="Meta de dolarização vigente")
async def get_dolar_goal(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> DolarGoalResponse:
    return await _read_typed("DOLARIZACAO", workspace.id, repo=repo, db=db)  # type: ignore[return-value]


@router.get("/dolarizacao/history", response_model=DolarGoalHistoryResponse,
            summary="Histórico de versões da meta de dolarização")
async def get_dolar_goal_history(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> DolarGoalHistoryResponse:
    responses = await _history_typed("DOLARIZACAO", workspace.id, repo=repo, db=db)
    return DolarGoalHistoryResponse(goals=responses, total=len(responses))  # type: ignore[arg-type]


@router.put("/dolarizacao", response_model=DolarGoalResponse,
            summary="Cria nova versão da meta de dolarização",
            dependencies=[Depends(require_write_role)])
async def upsert_dolar_goal(
    body: DolarGoalUpsertCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> DolarGoalResponse:
    return await _write_typed(  # type: ignore[return-value]
        "DOLARIZACAO", body.inputs, body.notes,
        workspace=workspace, user=user, repo=repo, db=db,
    )


# ALOCACAO_ALVO (F8.5) ═══════════════════════════════════════════════════


@router.post("/alocacao/compute", response_model=AlocacaoGoalComputeResponse,
             summary="Dry-run: valida alocação-alvo")
async def compute_alocacao_goal(
    body: AlocacaoGoalComputeRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
) -> AlocacaoGoalComputeResponse:
    return compute_alocacao_projection(body)


@router.get("/alocacao", response_model=AlocacaoGoalResponse,
            summary="Alocação-alvo vigente")
async def get_alocacao_goal(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> AlocacaoGoalResponse:
    return await _read_typed("ALOCACAO_ALVO", workspace.id, repo=repo, db=db)  # type: ignore[return-value]


@router.get("/alocacao/history", response_model=AlocacaoGoalHistoryResponse,
            summary="Histórico de versões da alocação-alvo")
async def get_alocacao_goal_history(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> AlocacaoGoalHistoryResponse:
    responses = await _history_typed("ALOCACAO_ALVO", workspace.id, repo=repo, db=db)
    return AlocacaoGoalHistoryResponse(goals=responses, total=len(responses))  # type: ignore[arg-type]


@router.put("/alocacao", response_model=AlocacaoGoalResponse,
            summary="Cria nova versão da alocação-alvo",
            dependencies=[Depends(require_write_role)])
async def upsert_alocacao_goal(
    body: AlocacaoGoalUpsertCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: GoalRepository = Depends(_get_repo),
) -> AlocacaoGoalResponse:
    return await _write_typed(  # type: ignore[return-value]
        "ALOCACAO_ALVO", body.inputs, body.notes,
        workspace=workspace, user=user, repo=repo, db=db,
    )


# Tasks linked to a goal (cross-aggregate read) ══════════════════════════


@router.get("/{goal_id}/tasks", response_model=TaskListResponse,
            summary="Tarefas vinculadas a esta meta")
async def list_tasks_for_goal(
    goal_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    include_done: bool = False,
) -> TaskListResponse:
    filters = TaskFilters(related_goal_id=goal_id, include_done=include_done)
    tasks = await task_service.list_tasks(workspace.id, filters, db=db)
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
    )
