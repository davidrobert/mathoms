"""Use case: partial update (deep merge) do blob ``PipelineConfig``."""

from __future__ import annotations

from backend.app.application.config_blob._protocols import (
    ConfigBlobRepositoryProtocol,
    GlobalDefaultsLoaderProtocol,
)
from backend.app.models.config_blob import PipelineConfig
from backend.app.schemas.dto.config_blob import (
    PipelineConfigResponse,
    PipelineConfigUpdateCommand,
    deep_merge,
    pipeline_blob_to_response,
)


async def update_pipeline_config(
    cmd: PipelineConfigUpdateCommand,
    *,
    workspace_id: str,
    repo: ConfigBlobRepositoryProtocol,
    defaults: GlobalDefaultsLoaderProtocol,
) -> PipelineConfigResponse:
    """Mescla fields presentes no ``cmd`` na config vigente (ou no default)
    e persiste. Caller commita — use case não fecha transação (R14).
    """
    existing = await repo.get_config_json(workspace_id, PipelineConfig)
    base = existing if existing is not None else defaults.load_json("pipeline.json")
    merged = deep_merge(base, cmd.model_dump(exclude_unset=True))
    await repo.upsert(workspace_id, PipelineConfig, merged)
    return pipeline_blob_to_response(merged)
