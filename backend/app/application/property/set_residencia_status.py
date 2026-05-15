"""Use case: seta `workspaces.residencia_status` (ADR-215 P4)."""

from __future__ import annotations

from backend.app.models import (
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    RESIDENCIA_STATUS_OWNED,
)
from backend.app.repositories.property_repository import PropertyRepository
from backend.app.schemas.dto.property import (
    ResidenciaStatusCommand,
    ResidenciaStatusResponse,
)


async def set_residencia_status(
    workspace_id: str,
    cmd: ResidenciaStatusCommand,
    *,
    repo: PropertyRepository,
) -> ResidenciaStatusResponse:
    """Set status tripartite. `rented`/`undeclared` apaga override `residencia_principal`."""
    cmd.validate_enums()

    workspace = await repo.get_workspace(workspace_id)
    if workspace is None:
        raise LookupError(f"workspace {workspace_id} não encontrado")

    workspace.residencia_status = cmd.status

    # Mudar de `owned` para `rented`/`undeclared` invalida override de
    # residencia_principal — sem isso, o filtro lazy split continuaria
    # apontando para um imóvel marcado, contradizendo o novo status.
    if cmd.status != RESIDENCIA_STATUS_OWNED:
        await repo.delete_overrides_with_classification(
            workspace_id, CLASSIFICATION_RESIDENCIA_PRINCIPAL
        )

    await repo._db.commit()  # type: ignore[attr-defined]
    return ResidenciaStatusResponse(workspace_id=workspace_id, status=cmd.status)
