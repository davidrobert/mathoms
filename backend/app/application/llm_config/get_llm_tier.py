"""Use case: resolve tier corrente do workspace (free/premium)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.llm_config import LLMConfig
from backend.app.schemas.llm import LLMTierResponse
from backend.app.services.pipeline_service import resolve_llm_tier_async


async def get_llm_tier(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> LLMTierResponse:
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == workspace_id))
    cfg = result.scalar_one_or_none()
    tier = await resolve_llm_tier_async(db, workspace_id)
    return LLMTierResponse(
        tier=tier,
        has_llm_config=cfg is not None,
        provider=cfg.provider if cfg else None,
        model=cfg.model_name if cfg else None,
    )
