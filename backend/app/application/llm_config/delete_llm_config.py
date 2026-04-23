"""Use case: remove config LLM do workspace (reverte para free tier)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.models.llm_config import LLMConfig


async def delete_llm_config(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> None:
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == workspace_id))
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise NotFoundError("Configuração LLM não encontrada")
    await db.delete(cfg)
    await db.commit()
