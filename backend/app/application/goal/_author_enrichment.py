"""Enriquecimento de ``created_by_name`` em respostas tipadas de Goal.

Resolve IDs de autor para ``full_name`` e acopla na resposta Pydantic.
Extraído de ``backend/app/api/goals.py`` (A6e.4) para manter o router
fino: handlers apenas orquestram repo + use case + este enrichment.
"""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User


async def resolve_author_names(
    user_ids: Iterable[str], *, db: AsyncSession
) -> dict[str, str]:
    ids = [uid for uid in user_ids if uid]
    if not ids:
        return {}
    rows = await db.execute(select(User).where(User.id.in_(ids)))
    return {u.id: u.full_name for u in rows.scalars().all()}


async def attach_author_name(resp: BaseModel, *, db: AsyncSession) -> BaseModel:
    """Enriquece ``created_by_name`` a partir de ``created_by`` em ``resp``."""
    created_by = getattr(resp, "created_by", None)
    if not created_by:
        return resp
    names = await resolve_author_names({created_by}, db=db)
    return resp.model_copy(update={"created_by_name": names.get(created_by)})
