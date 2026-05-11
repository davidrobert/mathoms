"""Use case: lê apólice por id (com tenancy)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.protections._protocols import (
    ProtectionRepositoryProtocol,
)
from backend.app.schemas.dto.protection import (
    ProtectionResponse,
    protection_to_response,
)


async def get_protection(
    workspace_id: str,
    protection_id: str,
    *,
    repo: ProtectionRepositoryProtocol,
) -> ProtectionResponse:
    protection = await repo.get_by_id(workspace_id, protection_id)
    if protection is None:
        raise NotFoundError(
            f"Protection id={protection_id} não encontrada",
            code="protection_not_found",
        )
    return protection_to_response(protection)
