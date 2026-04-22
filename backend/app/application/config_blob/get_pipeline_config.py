"""Use case: leitura do blob ``PipelineConfig`` com fallback do disco."""

from __future__ import annotations

from backend.app.application.config_blob._protocols import (
    ConfigBlobRepositoryProtocol,
    GlobalDefaultsLoaderProtocol,
)
from backend.app.models.config_blob import PipelineConfig
from backend.app.schemas.dto.config_blob import (
    PipelineConfigResponse,
    pipeline_blob_to_response,
)


async def get_pipeline_config(
    workspace_id: str,
    *,
    repo: ConfigBlobRepositoryProtocol,
    defaults: GlobalDefaultsLoaderProtocol,
) -> PipelineConfigResponse:
    cfg_json = await repo.get_config_json(workspace_id, PipelineConfig)
    if cfg_json is None:
        cfg_json = defaults.load_json("pipeline.json")
    return pipeline_blob_to_response(cfg_json)
