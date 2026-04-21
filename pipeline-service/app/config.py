"""Settings for pipeline-service (env-driven, stateless)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineServiceSettings:
    host: str
    port: int
    redis_url: str | None
    workspace_storage_root: str | None
    log_format: str
    log_level: str


def load_settings() -> PipelineServiceSettings:
    """Build settings from env. Called lazily by `main.create_app`."""
    return PipelineServiceSettings(
        host=os.environ.get("PIPELINE_SERVICE_HOST", "0.0.0.0"),
        port=int(os.environ.get("PIPELINE_SERVICE_PORT", "8001")),
        redis_url=os.environ.get("REDIS_URL"),
        workspace_storage_root=os.environ.get("WORKSPACE_STORAGE_ROOT"),
        log_format=os.environ.get("MATHOMS_LOG_FORMAT", "json"),
        log_level=os.environ.get("MATHOMS_LOG_LEVEL", "INFO"),
    )
