"""Category override API — writes hit ``workspace_category_overrides`` (A7.3 · ADR-137).

Endpoints novos sob ``/workspaces/{id}/config/category-overrides`` complementam
os endpoints legados em ``/workspaces/{id}/config/categories`` (que A7.5 vai
remover). Read-path do frontend continua usando os legados; novos endpoints
permitem escrever overrides explícitos. ADR-137 §Decisão.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.category.override_use_cases import (
    disable_category_override,
    list_categories_resolved,
    reset_category_override,
    upsert_category_override,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace
from backend.app.schemas.dto.category import (
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateCommand,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/config",
    tags=["config", "category-overrides"],
)


class CategoryOverrideStatus(BaseModel):
    """Status de override (delete confirma)."""

    template_key: str = Field(..., min_length=1, max_length=100)
    status: str = Field(..., pattern=r"^(disabled|reset|upserted)$")


@router.get(
    "/category-overrides/resolved",
    response_model=CategoryListResponse,
)
async def list_resolved_categories(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> CategoryListResponse:
    """Lista categorias resolvidas (template + overrides) — espelho do GET legado."""
    return await list_categories_resolved(workspace.id, db=db)


@router.put(
    "/category-overrides/{template_key}",
    response_model=CategoryResponse,
)
async def upsert_override(
    template_key: str,
    body: CategoryUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Cria/atualiza override do workspace para a ``template_key`` dada."""
    return await upsert_category_override(
        template_key, body, workspace_id=workspace.id, db=db
    )


@router.delete(
    "/category-overrides/{template_key}",
    response_model=CategoryOverrideStatus,
)
async def disable_override(
    template_key: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> CategoryOverrideStatus:
    """Desabilita categoria via override.disabled=True (não apaga o override)."""
    await disable_category_override(template_key, workspace_id=workspace.id, db=db)
    return CategoryOverrideStatus(template_key=template_key, status="disabled")


@router.post(
    "/category-overrides/{template_key}/reset",
    response_model=CategoryOverrideStatus,
    status_code=status.HTTP_200_OK,
)
async def reset_override(
    template_key: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> CategoryOverrideStatus:
    """Apaga override → categoria volta ao default do template."""
    await reset_category_override(template_key, workspace_id=workspace.id, db=db)
    return CategoryOverrideStatus(template_key=template_key, status="reset")
