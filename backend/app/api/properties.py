"""Property API router (ADR-215 P4)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.property import (
    list_properties,
    set_imoveis_no_if,
    set_property_classification,
    set_residencia_status,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.property_repository import PropertyRepository
from backend.app.schemas.dto.property import (
    ImoveisNoIfCommand,
    ImoveisNoIfResponse,
    PropertyClassificationCommand,
    PropertyListResponse,
    PropertyResponse,
    ResidenciaStatusCommand,
    ResidenciaStatusResponse,
)
from backend.app.services.crypto import read_artifact_content

logger = logging.getLogger("mathoms.properties")


router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["properties"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> PropertyRepository:
    return PropertyRepository(db)


async def _fetch_contribuinte_endereco(workspace_id: str, db: AsyncSession) -> Optional[str]:
    """Lê `contribuinte.endereco` mais recente dos artifacts E1.6 do workspace.

    Retorna None quando não há IRPF processado (lazy fill ADR-215 P1).
    """
    from sqlalchemy import select

    from backend.app.models import PipelineArtifact

    stmt = (
        select(PipelineArtifact)
        .where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage == "extract_irpf_full",
        )
        .order_by(PipelineArtifact.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    artifact = result.scalar_one_or_none()
    if artifact is None:
        return None
    contribuinte = (read_artifact_content(artifact.content_json) or {}).get("contribuinte") or {}
    endereco = contribuinte.get("endereco")
    return endereco if isinstance(endereco, str) and endereco else None


@router.get("/properties", response_model=PropertyListResponse)
async def list_workspace_properties(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: PropertyRepository = Depends(_get_repo),
    _user: User = Depends(get_current_user),
) -> PropertyListResponse:
    """Lista imóveis classificáveis com fuzzy suggestion."""
    endereco = await _fetch_contribuinte_endereco(workspace.id, db)
    response = await list_properties(workspace.id, repo=repo, contribuinte_endereco=endereco)
    logger.info(
        "list_properties workspace=%s n=%d has_endereco=%s",
        workspace.id,
        len(response.properties),
        endereco is not None,
    )
    return response


@router.put(
    "/properties/{property_id}/classification",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
)
async def put_property_classification(
    property_id: str,
    cmd: PropertyClassificationCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: PropertyRepository = Depends(_get_repo),
    user: User = Depends(get_current_user),
) -> PropertyResponse:
    """Idempotente. residencia_principal automaticamente seta status=owned."""
    try:
        response = await set_property_classification(
            workspace.id,
            property_id,
            cmd,
            repo=repo,
            user_id=user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    logger.info(
        "set_property_classification workspace=%s property=%s class=%s source=%s",
        workspace.id,
        property_id,
        cmd.classification,
        cmd.override_source,
    )
    return response


@router.put("/residencia-status", response_model=ResidenciaStatusResponse)
async def put_residencia_status(
    cmd: ResidenciaStatusCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: PropertyRepository = Depends(_get_repo),
    _user: User = Depends(get_current_user),
) -> ResidenciaStatusResponse:
    """rented/undeclared apaga overrides residencia_principal."""
    try:
        response = await set_residencia_status(workspace.id, cmd, repo=repo)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    logger.info(
        "set_residencia_status workspace=%s status=%s",
        workspace.id,
        cmd.status,
    )
    return response


@router.put("/imoveis-no-if", response_model=ImoveisNoIfResponse)
async def put_imoveis_no_if(
    cmd: ImoveisNoIfCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: PropertyRepository = Depends(_get_repo),
    user: User = Depends(get_current_user),
) -> ImoveisNoIfResponse:
    """ADR-222: flippa per-workspace `imoveis_no_if` (cat_2 entra/sai do investível efetivo)."""
    try:
        response = await set_imoveis_no_if(workspace.id, cmd, repo=repo, user_id=user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    logger.info(
        "set_imoveis_no_if workspace=%s value=%s by=%s",
        workspace.id,
        cmd.imoveis_no_if,
        user.id,
    )
    return response
