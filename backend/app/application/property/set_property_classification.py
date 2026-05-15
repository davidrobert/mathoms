"""Use case: seta classification de um imóvel (ADR-215 P4)."""

from __future__ import annotations

from typing import Optional

from backend.app.models import (
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    RESIDENCIA_STATUS_OWNED,
)
from backend.app.repositories.property_repository import PropertyRepository
from backend.app.schemas.dto.property import (
    PropertyClassificationCommand,
    PropertyResponse,
)


async def set_property_classification(
    workspace_id: str,
    property_id: str,
    cmd: PropertyClassificationCommand,
    *,
    repo: PropertyRepository,
    user_id: Optional[str],
) -> PropertyResponse:
    """Idempotente. Marcar residencia_principal → também seta residencia_status=owned."""
    cmd.validate_enums()

    identity = await repo.get_identity(workspace_id, property_id)
    if identity is None:
        raise LookupError(f"property {property_id} não encontrado no workspace {workspace_id}")

    override = await repo.upsert_override(
        workspace_id=workspace_id,
        property_id=property_id,
        classification=cmd.classification,
        override_source=cmd.override_source,
        created_by_user_id=user_id,
    )

    # Marcar como residencia_principal implica residencia_status=owned.
    if cmd.classification == CLASSIFICATION_RESIDENCIA_PRINCIPAL:
        workspace = await repo.get_workspace(workspace_id)
        if workspace is not None and workspace.residencia_status != RESIDENCIA_STATUS_OWNED:
            workspace.residencia_status = RESIDENCIA_STATUS_OWNED

    await repo._db.commit()  # type: ignore[attr-defined]
    await repo._db.refresh(override)  # type: ignore[attr-defined]

    return PropertyResponse(
        property_id=identity.id,
        titular_key=identity.titular_key,
        codigo_rfb=identity.codigo_rfb,
        descricao_sample=identity.descricao_sample,
        endereco_canonical=identity.endereco_canonical,
        first_seen_year=identity.first_seen_year,
        low_confidence=identity.low_confidence,
        classification=override.classification,
        override_source=override.override_source,
        classification_set_at=override.updated_at,
    )
