"""Risks API — router fino (A10.4 · ADR-101 R15/R16 · ADR-178).

Endpoints sob ``/workspaces/{workspace_id}/risks/...`` delegam aos use
cases em :mod:`backend.app.application.risks`. Erros de domínio
traduzidos para HTTP por handlers globais em ``main.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.risks import (
    create_risk as _uc_create_risk,
)
from backend.app.application.risks import (
    delete_risk as _uc_delete_risk,
)
from backend.app.application.risks import (
    get_risk as _uc_get_risk,
)
from backend.app.application.risks import (
    link_mitigation as _uc_link_mitigation,
)
from backend.app.application.risks import (
    list_risks as _uc_list_risks,
)
from backend.app.application.risks import (
    unlink_mitigation as _uc_unlink_mitigation,
)
from backend.app.application.risks import (
    update_risk as _uc_update_risk,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.workspace import Workspace
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.schemas.dto.risk import (
    RiskCreateCommand,
    RiskListResponse,
    RiskMitigationLinkCommand,
    RiskResponse,
    RiskUpdateCommand,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/risks", tags=["risks"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> RiskRepository:
    return RiskRepository(db)


def _get_decision_repo(db: AsyncSession = Depends(get_db)) -> DecisionRepository:
    return DecisionRepository(db)


@router.get("", response_model=RiskListResponse)
async def list_risks(
    workspace: Workspace = Depends(get_current_workspace),
    repo: RiskRepository = Depends(_get_repo),
) -> RiskListResponse:
    return await _uc_list_risks(workspace.id, repo=repo)


@router.post(
    "",
    response_model=RiskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def create_risk(
    payload: RiskCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: RiskRepository = Depends(_get_repo),
) -> RiskResponse:
    response = await _uc_create_risk(payload, workspace_id=workspace.id, repo=repo)
    await db.commit()
    return response


@router.get("/{risk_id}", response_model=RiskResponse)
async def get_risk(
    risk_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: RiskRepository = Depends(_get_repo),
) -> RiskResponse:
    return await _uc_get_risk(workspace.id, risk_id, repo=repo)


@router.patch(
    "/{risk_id}",
    response_model=RiskResponse,
    dependencies=[Depends(require_write_role)],
)
async def update_risk(
    risk_id: str,
    payload: RiskUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: RiskRepository = Depends(_get_repo),
) -> RiskResponse:
    response = await _uc_update_risk(
        payload,
        workspace_id=workspace.id,
        risk_id=risk_id,
        repo=repo,
    )
    await db.commit()
    return response


@router.delete(
    "/{risk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_role)],
)
async def delete_risk(
    risk_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: RiskRepository = Depends(_get_repo),
) -> None:
    await _uc_delete_risk(workspace_id=workspace.id, risk_id=risk_id, repo=repo)
    await db.commit()


@router.post(
    "/{risk_id}/mitigations",
    response_model=RiskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def link_mitigation(
    risk_id: str,
    payload: RiskMitigationLinkCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: RiskRepository = Depends(_get_repo),
    decision_repo: DecisionRepository = Depends(_get_decision_repo),
) -> RiskResponse:
    response = await _uc_link_mitigation(
        payload,
        workspace_id=workspace.id,
        risk_id=risk_id,
        risk_repo=repo,
        decision_repo=decision_repo,
    )
    await db.commit()
    return response


@router.delete(
    "/{risk_id}/mitigations/{decision_id}",
    response_model=RiskResponse,
    dependencies=[Depends(require_write_role)],
)
async def unlink_mitigation(
    risk_id: str,
    decision_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: RiskRepository = Depends(_get_repo),
) -> RiskResponse:
    response = await _uc_unlink_mitigation(
        workspace_id=workspace.id,
        risk_id=risk_id,
        decision_id=decision_id,
        risk_repo=repo,
    )
    await db.commit()
    return response
