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
    CollapseEnforceResponse,
    CollapseEnforceUpdate,
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
from backend.app.services.internal_ops.set_collapse_enforce import set_collapse_enforce

router = APIRouter(prefix="/workspaces")

_ERROR_STATUS = {
    "workspace_not_found": status.HTTP_404_NOT_FOUND,
    # 409: o estado do workspace impede ligar agora — não é erro de request.
    "medicao_ausente": status.HTTP_409_CONFLICT,
    "medicao_velha": status.HTTP_409_CONFLICT,
    "preflight_reprovado": status.HTTP_409_CONFLICT,
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


# A única porta para `cross_document_collapse_enforce_enabled` — a flag está em
# `OPERATOR_ONLY`, logo `PUT /feature-flags/{flag}` a recusa com 422.
@router.patch("/{workspace_id}/collapse-enforce", response_model=CollapseEnforceResponse)
async def admin_set_collapse_enforce(
    workspace_id: str,
    payload: CollapseEnforceUpdate,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> CollapseEnforceResponse:
    """Liga/desliga o colapso cross-documento em enforce (A40.l2 §3e · [[ADR-364]])."""
    result = await set_collapse_enforce(
        db, workspace_id, enabled=payload.enabled, actor=principal.actor
    )
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return CollapseEnforceResponse(**result.details)
