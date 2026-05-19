"""API router do card Exposição Cambial V2 (ADR-224; GET read-time + POST/DELETE/GET overrides per-workspace; response_model ADR-102 R18)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.exposicao_cambial_v2 import (
    compute_exposicao_cambial_v2,
    delete_asset_override,
    list_asset_overrides,
    upsert_asset_override,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.dto.exposicao_cambial import (
    AssetOverrideCommand,
    AssetOverrideListResponse,
    AssetOverrideResponse,
    ExposicaoCambialResponse,
)

logger = logging.getLogger("mathoms.exposicao_cambial")

router = APIRouter(prefix="/workspaces/{workspace_id}/cards", tags=["cards"])


@router.get("/exposicao-cambial", response_model=ExposicaoCambialResponse)
async def get_exposicao_cambial(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ExposicaoCambialResponse:
    """Retorna exposição cambial V2 recomputada read-time com catalog + overrides correntes."""
    response = await compute_exposicao_cambial_v2(workspace.id, db)
    logger.info(
        "mathoms.exposicao_cambial.computed",
        extra={
            "workspace_id": workspace.id,
            "total_brl_str": str(response.total_brl),
            "tier": response.tier,
            "ativos_count": len(response.ativos_contribuintes),
        },
    )
    return response


@router.get("/exposicao-cambial/overrides", response_model=AssetOverrideListResponse)
async def list_overrides(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> AssetOverrideListResponse:
    """Lista overrides de lastro per-workspace."""
    overrides = await list_asset_overrides(workspace.id, db)
    return AssetOverrideListResponse(workspace_id=workspace.id, overrides=overrides)


@router.post(
    "/exposicao-cambial/overrides",
    response_model=AssetOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_update_override(
    command: AssetOverrideCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetOverrideResponse:
    """Declara override sticky `(workspace_id, match_kind, asset_match_key)` ADR-224 §2."""
    response = await upsert_asset_override(workspace.id, command, db, user_id=user.id)
    logger.info(
        "mathoms.exposicao_cambial.override_upserted",
        extra={
            "workspace_id": workspace.id,
            "match_kind": command.match_kind,
            "lastro_moeda": command.lastro_moeda,
            "user_id": user.id,
        },
    )
    return response


@router.delete(
    "/exposicao-cambial/overrides/{match_kind}/{asset_match_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def remove_override(
    match_kind: str,
    asset_match_key: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Response:
    """Remove override (revert para catalog/fallback). 204 mesmo se ausente (idempotente)."""
    removed = await delete_asset_override(workspace.id, match_kind, asset_match_key, db)
    logger.info(
        "mathoms.exposicao_cambial.override_deleted",
        extra={
            "workspace_id": workspace.id,
            "match_kind": match_kind,
            "removed": removed,
        },
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
