"""Use case: leitura do blob ``ReportLayout`` com fallback do disco (YAML)."""

from __future__ import annotations

from backend.app.application.config_blob._protocols import (
    ConfigBlobRepositoryProtocol,
    GlobalDefaultsLoaderProtocol,
)
from backend.app.models.config_blob import ReportLayout
from backend.app.schemas.dto.config_blob import (
    ReportLayoutResponse,
    report_layout_to_response,
)


async def get_report_layout(
    workspace_id: str,
    *,
    repo: ConfigBlobRepositoryProtocol,
    defaults: GlobalDefaultsLoaderProtocol,
) -> ReportLayoutResponse:
    cfg_json = await repo.get_config_json(workspace_id, ReportLayout)
    if cfg_json is None:
        cfg_json = defaults.load_yaml("report_layout.yaml")
    return report_layout_to_response(cfg_json)
