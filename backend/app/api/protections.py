"""Protections API — router fino (ADR-101 R15/R16 · ADR-192)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.protections import (
    cancel_protection as _uc_cancel_protection,
)
from backend.app.application.protections import (
    create_protection as _uc_create_protection,
)
from backend.app.application.protections import (
    get_protection as _uc_get_protection,
)
from backend.app.application.protections import (
    link_to_risk as _uc_link_to_risk,
)
from backend.app.application.protections import (
    list_protections as _uc_list_protections,
)
from backend.app.application.protections import (
    unlink_from_risk as _uc_unlink_from_risk,
)
from backend.app.application.protections import (
    update_protection as _uc_update_protection,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.workspace import Workspace
from backend.app.repositories.protection_repository import ProtectionRepository
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.schemas.dto.protection import (
    ProtectionBundleResponse,
    ProtectionCancelCommand,
    ProtectionCreateCommand,
    ProtectionLinkToRiskCommand,
    ProtectionListResponse,
    ProtectionResponse,
    ProtectionUpdateCommand,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/protections", tags=["protections"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> ProtectionRepository:
    return ProtectionRepository(db)


def _get_risk_repo(db: AsyncSession = Depends(get_db)) -> RiskRepository:
    return RiskRepository(db)


@router.get("", response_model=ProtectionListResponse)
async def list_protections(
    workspace: Workspace = Depends(get_current_workspace),
    repo: ProtectionRepository = Depends(_get_repo),
) -> ProtectionListResponse:
    return await _uc_list_protections(workspace.id, repo=repo)


@router.post(
    "",
    response_model=ProtectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def create_protection(
    payload: ProtectionCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ProtectionRepository = Depends(_get_repo),
) -> ProtectionResponse:
    response = await _uc_create_protection(payload, workspace_id=workspace.id, repo=repo)
    await db.commit()
    return response


@router.get("/{protection_id}", response_model=ProtectionResponse)
async def get_protection(
    protection_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: ProtectionRepository = Depends(_get_repo),
) -> ProtectionResponse:
    return await _uc_get_protection(workspace.id, protection_id, repo=repo)


@router.patch(
    "/{protection_id}",
    response_model=ProtectionResponse,
    dependencies=[Depends(require_write_role)],
)
async def update_protection(
    protection_id: str,
    payload: ProtectionUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ProtectionRepository = Depends(_get_repo),
) -> ProtectionResponse:
    response = await _uc_update_protection(
        payload,
        workspace_id=workspace.id,
        protection_id=protection_id,
        repo=repo,
    )
    await db.commit()
    return response


@router.post(
    "/{protection_id}/cancel",
    response_model=ProtectionResponse,
    dependencies=[Depends(require_write_role)],
)
async def cancel_protection(
    protection_id: str,
    payload: ProtectionCancelCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ProtectionRepository = Depends(_get_repo),
) -> ProtectionResponse:
    response = await _uc_cancel_protection(
        payload,
        workspace_id=workspace.id,
        protection_id=protection_id,
        repo=repo,
    )
    await db.commit()
    return response


@router.post(
    "/{protection_id}/risks",
    response_model=ProtectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def link_to_risk(
    protection_id: str,
    payload: ProtectionLinkToRiskCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ProtectionRepository = Depends(_get_repo),
    risk_repo: RiskRepository = Depends(_get_risk_repo),
) -> ProtectionResponse:
    response = await _uc_link_to_risk(
        payload,
        workspace_id=workspace.id,
        protection_id=protection_id,
        repo=repo,
        risk_repo=risk_repo,
    )
    await db.commit()
    return response


@router.delete(
    "/{protection_id}/risks/{risk_id}",
    response_model=ProtectionResponse,
    dependencies=[Depends(require_write_role)],
)
async def unlink_from_risk(
    protection_id: str,
    risk_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: ProtectionRepository = Depends(_get_repo),
    risk_repo: RiskRepository = Depends(_get_risk_repo),
) -> ProtectionResponse:
    response = await _uc_unlink_from_risk(
        workspace_id=workspace.id,
        protection_id=protection_id,
        risk_id=risk_id,
        repo=repo,
        risk_repo=risk_repo,
    )
    await db.commit()
    return response


protection_bundle_router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["protections"])


@protection_bundle_router.get("/protection-bundle", response_model=ProtectionBundleResponse)
async def get_protection_bundle(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ProtectionBundleResponse:
    """Bundle agregado consumido pelo renderer S9 (ADR-192 §D2)."""
    from backend.app.services.pipeline_adapter import build_protection_bundle

    return await build_protection_bundle(workspace.id, db=db)
