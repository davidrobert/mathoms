"""Use case: leitura do blob ``TransferConfig`` com fallback do disco (ADR-133)."""

from __future__ import annotations

from backend.app.application.config_blob._protocols import (
    ConfigBlobRepositoryProtocol,
    GlobalDefaultsLoaderProtocol,
)
from backend.app.models.config_blob import TransferConfig
from backend.app.schemas.dto.config_blob import (
    TransferConfigResponse,
    transfer_blob_to_response,
)

_FAMILY_BLOCK_KEY = "transferencias_internas"


async def get_transfer_config(
    workspace_id: str,
    *,
    repo: ConfigBlobRepositoryProtocol,
    defaults: GlobalDefaultsLoaderProtocol,
) -> TransferConfigResponse:
    cfg_json = await repo.get_config_json(workspace_id, TransferConfig)
    if cfg_json is None:
        family = defaults.load_json("family_members.json") or {}
        cfg_json = family.get(_FAMILY_BLOCK_KEY) or {}
    return transfer_blob_to_response(cfg_json)
