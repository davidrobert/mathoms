"""Categories API — router fino (A6e.3 slice 2 · ADR-101 R15/R16).

Endpoints sob ``/workspaces/{workspace_id}/config/categories`` delegam a
use cases em :mod:`backend.app.application.category`. Erros de domínio
traduzidos para HTTP por handlers globais em ``main.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.category import (
    create_category as uc_create_category,
)
from backend.app.application.category import (
    delete_category as uc_delete_category,
)
from backend.app.application.category import (
    list_categories as uc_list_categories,
)
from backend.app.application.category import (
    update_category as uc_update_category,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace
from backend.app.repositories.category_repository import CategoryRepository
from backend.app.schemas.dto.category import (
    CategoryCreateCommand,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateCommand,
)
router = APIRouter(prefix="/workspaces/{workspace_id}/config", tags=["config"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> CategoryRepository:
    return CategoryRepository(db)


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    workspace: Workspace = Depends(get_current_workspace),
    repo: CategoryRepository = Depends(_get_repo),
) -> CategoryListResponse:
    # A8.0: `config/categorization.json` deletado em A7.5; workspace sem rows
    # retorna lista vazia. A7.3 catalog/override é o caminho moderno; este
    # endpoint legacy continua para compat frontend até migração futura.
    return await uc_list_categories(workspace.id, repo=repo)


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    body: CategoryCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: CategoryRepository = Depends(_get_repo),
) -> CategoryResponse:
    return await uc_create_category(body, workspace_id=workspace.id, repo=repo)


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    body: CategoryUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    repo: CategoryRepository = Depends(_get_repo),
) -> CategoryResponse:
    return await uc_update_category(category_id, body, workspace_id=workspace.id, repo=repo)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: CategoryRepository = Depends(_get_repo),
) -> None:
    await uc_delete_category(category_id, workspace_id=workspace.id, repo=repo)
