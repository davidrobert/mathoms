"""Use case: lista apólices do workspace."""

from __future__ import annotations

from backend.app.application.protections._protocols import (
    ProtectionRepositoryProtocol,
)
from backend.app.schemas.dto.protection import (
    ProtectionListResponse,
    protection_to_response,
)


async def list_protections(
    workspace_id: str,
    *,
    repo: ProtectionRepositoryProtocol,
) -> ProtectionListResponse:
    protections = await repo.list_by_workspace(workspace_id)
    items = [protection_to_response(p) for p in protections]
    return ProtectionListResponse(protections=items, total=len(items))
