"""API router do card Exposição Cambial V2 (ADR-224; `GET /v1/workspaces/{ws}/cards/exposicao-cambial`; read-time service-layer; response_model ADR-102 R18)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.exposicao_cambial_v2 import compute_exposicao_cambial_v2
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.dto.exposicao_cambial import ExposicaoCambialResponse

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
