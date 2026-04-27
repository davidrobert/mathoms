"""Decisions API — router fino (A7.2a · ADR-101 R15/R16 · ADR-136).

Endpoints sob ``/workspaces/{workspace_id}/decisions/...`` delegam aos
use cases em :mod:`backend.app.application.decisions`. Erros de domínio
traduzidos para HTTP por handlers globais em ``main.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.decisions import (
    create_decision as _uc_create_decision,
)
from backend.app.application.decisions import (
    get_decision as _uc_get_decision,
)
from backend.app.application.decisions import (
    list_decisions as _uc_list_decisions,
)
from backend.app.application.decisions import (
    mark_decision_executed as _uc_mark_decision_executed,
)
from backend.app.application.decisions import (
    supersede_decision as _uc_supersede_decision,
)
from backend.app.application.decisions import (
    update_decision as _uc_update_decision,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.schemas.dto.decision import (
    DecisionCreateCommand,
    DecisionExecuteCommand,
    DecisionListResponse,
    DecisionResponse,
    DecisionSupersedeCommand,
    DecisionUpdateCommand,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/decisions", tags=["decisions"]
)


def _get_repo(db: AsyncSession = Depends(get_db)) -> DecisionRepository:
    return DecisionRepository(db)


def _actor_id(user: User) -> str:
    return f"user:{user.id}"


@router.get("", response_model=DecisionListResponse)
async def list_decisions(
    workspace: Workspace = Depends(get_current_workspace),
    repo: DecisionRepository = Depends(_get_repo),
) -> DecisionListResponse:
    return await _uc_list_decisions(workspace.id, repo=repo)


@router.post(
    "",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def create_decision(
    payload: DecisionCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: DecisionRepository = Depends(_get_repo),
) -> DecisionResponse:
    response = await _uc_create_decision(
        payload, workspace_id=workspace.id, repo=repo, actor=_actor_id(user)
    )
    await db.commit()
    return response


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: DecisionRepository = Depends(_get_repo),
) -> DecisionResponse:
    return await _uc_get_decision(workspace.id, decision_id, repo=repo)


@router.patch(
    "/{decision_id}",
    response_model=DecisionResponse,
    dependencies=[Depends(require_write_role)],
)
async def update_decision(
    decision_id: str,
    payload: DecisionUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: DecisionRepository = Depends(_get_repo),
) -> DecisionResponse:
    response = await _uc_update_decision(
        payload,
        workspace_id=workspace.id,
        decision_id=decision_id,
        repo=repo,
        actor=_actor_id(user),
    )
    await db.commit()
    return response


@router.post(
    "/{decision_id}/execute",
    response_model=DecisionResponse,
    dependencies=[Depends(require_write_role)],
)
async def execute_decision(
    decision_id: str,
    payload: DecisionExecuteCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: DecisionRepository = Depends(_get_repo),
) -> DecisionResponse:
    response = await _uc_mark_decision_executed(
        payload,
        workspace_id=workspace.id,
        decision_id=decision_id,
        repo=repo,
        actor=_actor_id(user),
    )
    await db.commit()
    return response


@router.post(
    "/{decision_id}/supersede",
    response_model=DecisionResponse,
    dependencies=[Depends(require_write_role)],
)
async def supersede_decision(
    decision_id: str,
    payload: DecisionSupersedeCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: DecisionRepository = Depends(_get_repo),
) -> DecisionResponse:
    response = await _uc_supersede_decision(
        payload,
        workspace_id=workspace.id,
        old_decision_id=decision_id,
        repo=repo,
        actor=_actor_id(user),
    )
    await db.commit()
    return response
