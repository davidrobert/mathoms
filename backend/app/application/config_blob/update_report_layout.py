"""Use case: replace total do blob ``ReportLayout``."""

from __future__ import annotations

from backend.app.application.config_blob._protocols import (
    ConfigBlobRepositoryProtocol,
)
from backend.app.models.config_blob import ReportLayout
from backend.app.schemas.dto.config_blob import (
    ReportLayoutResponse,
    ReportLayoutUpdateCommand,
    report_layout_to_response,
)


async def update_report_layout(
    cmd: ReportLayoutUpdateCommand,
    *,
    workspace_id: str,
    repo: ConfigBlobRepositoryProtocol,
) -> ReportLayoutResponse:
    cfg = await repo.upsert(workspace_id, ReportLayout, cmd.config_json)
    return report_layout_to_response(cfg.config_json)
