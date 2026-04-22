"""Use case: aplica override workspace-level numa feature flag.

``ValueError`` do serviço (flag desconhecida) é traduzido para
``ValidationError`` — handler global em ``main.py`` mapeia para 422.
"""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base import ValidationError
from backend.app.application.feature_flag.get_feature_flags import FlagsResponse
from backend.app.services import feature_flags_service


class FlagUpdateCommand(BaseModel):
    enabled: bool


async def set_feature_flag(
    workspace_id: str,
    flag: str,
    command: FlagUpdateCommand,
    *,
    db: AsyncSession,
) -> FlagsResponse:
    try:
        flags = await feature_flags_service.set_flag(
            workspace_id, flag, command.enabled, db=db
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    await db.commit()
    return FlagsResponse(flags=flags)
