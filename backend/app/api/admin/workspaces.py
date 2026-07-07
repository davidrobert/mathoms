"""Console interno — endpoints /admin/workspaces/{id}/* (ADR-116 + ADR-236 + A30.l1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.schemas.admin import (
    WorkspaceLLMBudgetResponse,
    WorkspaceLLMBudgetUpdate,
)
from backend.app.schemas.business_profile import (
    BusinessProfile,
    BusinessProfileResponse,
)
from backend.app.services.internal_ops import (
    get_workspace_business_profile,
    update_workspace_business_profile,
    update_workspace_llm_budget,
)

router = APIRouter(prefix="/workspaces")

_ERROR_STATUS = {
    "workspace_not_found": status.HTTP_404_NOT_FOUND,
}


def _raise_from(result) -> None:
    http_status = _ERROR_STATUS.get(result.error or "", status.HTTP_400_BAD_REQUEST)
    raise HTTPException(status_code=http_status, detail=result.error)


@router.get("/{workspace_id}/business-profile", response_model=BusinessProfileResponse)
async def admin_get_business_profile(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> BusinessProfileResponse:
    """Operador lê o perfil tributário PJ; 404 se workspace inexistente."""
    result = await get_workspace_business_profile(db, workspace_id)
    if not result.ok:
        _raise_from(result)
    return BusinessProfileResponse(**result.details["profile"])


@router.patch("/{workspace_id}/business-profile", response_model=BusinessProfileResponse)
async def admin_update_business_profile(
    workspace_id: str,
    payload: BusinessProfile,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> BusinessProfileResponse:
    """Operador substitui o perfil tributário PJ (replace, não merge)."""
    result = await update_workspace_business_profile(
        db, workspace_id, actor=principal.actor, payload=payload
    )
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return BusinessProfileResponse(**result.details["profile"])


@router.patch("/{workspace_id}/llm-budget", response_model=WorkspaceLLMBudgetResponse)
async def admin_update_llm_budget(
    workspace_id: str,
    payload: WorkspaceLLMBudgetUpdate,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> WorkspaceLLMBudgetResponse:
    """Define ou remove o cap LLM mensal do workspace (A30.l1 · ADR-173)."""
    result = await update_workspace_llm_budget(
        db, workspace_id, actor=principal.actor, payload=payload
    )
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return WorkspaceLLMBudgetResponse(**result.details)
