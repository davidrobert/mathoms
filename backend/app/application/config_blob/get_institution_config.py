"""Use case: leitura do blob ``InstitutionConfig`` com fallback do disco."""

from __future__ import annotations

from backend.app.application.config_blob._protocols import (
    ConfigBlobRepositoryProtocol,
    GlobalDefaultsLoaderProtocol,
)
from backend.app.models.config_blob import InstitutionConfig
from backend.app.schemas.dto.config_blob import (
    InstitutionConfigResponse,
    institution_blob_to_response,
)


async def get_institution_config(
    workspace_id: str,
    *,
    repo: ConfigBlobRepositoryProtocol,
    defaults: GlobalDefaultsLoaderProtocol,
) -> InstitutionConfigResponse:
    cfg_json = await repo.get_config_json(workspace_id, InstitutionConfig)
    if cfg_json is None:
        cfg_json = defaults.load_json("institutions.json")
    return institution_blob_to_response(cfg_json)
