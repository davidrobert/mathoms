"""Use case: lê config LLM atual do workspace (ou None)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.llm_config._response import to_response
from backend.app.models.llm_config import LLMConfig
from backend.app.schemas.llm import LLMConfigResponse
from backend.app.services.vault import VaultService


async def get_llm_config(
    workspace_id: str,
    *,
    db: AsyncSession,
    vault: VaultService,
) -> LLMConfigResponse | None:
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == workspace_id))
    cfg = result.scalar_one_or_none()
    if cfg is None:
        return None
    return to_response(cfg, vault=vault)
