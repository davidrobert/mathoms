"""Use case: lê flags efetivas (defaults + overrides) do workspace."""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import feature_flags_service


class FlagsResponse(BaseModel):
    flags: dict[str, bool]


async def get_feature_flags(workspace_id: str, *, db: AsyncSession) -> FlagsResponse:
    flags = await feature_flags_service.get_flags(workspace_id, db=db)
    return FlagsResponse(flags=flags)
