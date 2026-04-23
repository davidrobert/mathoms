"""LLM Config router fino — per-workspace config + probe (A6e.4 · ADR-101 R15/R16)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.llm_config import (
    delete_llm_config as _delete_llm_config,
)
from backend.app.application.llm_config import (
    get_llm_config as _get_llm_config,
)
from backend.app.application.llm_config import (
    get_llm_tier as _get_llm_tier,
)
from backend.app.application.llm_config import (
    save_llm_config as _save_llm_config,
)
from backend.app.application.llm_config import (
    test_llm_connection as _test_llm_connection,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.workspace import Workspace
from backend.app.schemas.llm import (
    LLMConfigCreateRequest,
    LLMConfigResponse,
    LLMConfigTestRequest,
    LLMConfigTestResponse,
    LLMTierResponse,
)
from backend.app.services.vault import get_vault

router = APIRouter(
    prefix="/workspaces/{workspace_id}/config",
    tags=["llm"],
)


@router.get("/llm", response_model=LLMConfigResponse | None)
async def get_llm_config(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> LLMConfigResponse | None:
    return await _get_llm_config(workspace.id, db=db, vault=get_vault())


@router.put(
    "/llm",
    response_model=LLMConfigResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_write_role)],
)
async def save_llm_config(
    body: LLMConfigCreateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> LLMConfigResponse:
    return await _save_llm_config(workspace.id, body, db=db, vault=get_vault())


@router.delete(
    "/llm",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_role)],
)
async def delete_llm_config(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _delete_llm_config(workspace.id, db=db)


@router.post("/llm/test", response_model=LLMConfigTestResponse)
async def test_llm_connection(
    body: LLMConfigTestRequest | None = None,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> LLMConfigTestResponse:
    return await _test_llm_connection(workspace.id, body, db=db, vault=get_vault())


@router.get("/llm/tier", response_model=LLMTierResponse)
async def get_tier(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> LLMTierResponse:
    return await _get_llm_tier(workspace.id, db=db)
