"""Use case: replace total do blob ``TransferConfig`` (ADR-130)."""

from __future__ import annotations

from backend.app.application.config_blob._protocols import (
    ConfigBlobRepositoryProtocol,
)
from backend.app.models.config_blob import TransferConfig
from backend.app.schemas.dto.config_blob import (
    TransferConfigResponse,
    TransferConfigUpdateCommand,
    transfer_blob_to_response,
)


async def update_transfer_config(
    cmd: TransferConfigUpdateCommand,
    *,
    workspace_id: str,
    repo: ConfigBlobRepositoryProtocol,
) -> TransferConfigResponse:
    """Replace total — substitui as 4 listas/dict. Caller commita (R14)."""
    payload = cmd.model_dump()
    await repo.upsert(workspace_id, TransferConfig, payload)
    return transfer_blob_to_response(payload)
