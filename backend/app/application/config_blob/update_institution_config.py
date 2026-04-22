"""Use case: replace total do blob ``InstitutionConfig``."""

from __future__ import annotations

from backend.app.application.config_blob._protocols import (
    ConfigBlobRepositoryProtocol,
)
from backend.app.models.config_blob import InstitutionConfig
from backend.app.schemas.dto.config_blob import (
    InstitutionConfigResponse,
    InstitutionConfigUpdateCommand,
    institution_blob_to_response,
)


async def update_institution_config(
    cmd: InstitutionConfigUpdateCommand,
    *,
    workspace_id: str,
    repo: ConfigBlobRepositoryProtocol,
) -> InstitutionConfigResponse:
    """Substitui o ``config_json`` inteiro (sem merge) — shape é profundo
    demais para merge parcial fazer sentido.
    """
    cfg = await repo.upsert(workspace_id, InstitutionConfig, cmd.config_json)
    return institution_blob_to_response(cfg.config_json)
