"""Use case: lista membros de um workspace."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.workspace_members import MemberListResponse, MemberResponse
from backend.app.services import membership_service


async def list_members(workspace_id: str, *, db: AsyncSession) -> MemberListResponse:
    rows = await membership_service.list_members(workspace_id, db=db)
    return MemberListResponse(
        members=[
            MemberResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=m.role,  # type: ignore[arg-type]
                joined_at=m.joined_at,
                invited_by=m.invited_by,
            )
            for m, user in rows
        ],
        total=len(rows),
    )
