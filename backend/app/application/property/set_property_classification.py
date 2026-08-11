"""Use case: seta classification de um imóvel (ADR-215 P4)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import IntegrityError

from backend.app.application.base.errors import ConflictError
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

    if cmd.classification == CLASSIFICATION_RESIDENCIA_PRINCIPAL:
        await _reject_second_residencia_principal(workspace_id, property_id, repo=repo)

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

    try:
        await repo._db.commit()  # type: ignore[attr-defined]
    except IntegrityError as exc:
        # Backstop do partial-unique uq_workspace_one_residencia_principal: o
        # pre-check acima cobre o caso comum, mas duas requisições concorrentes
        # passam por ele antes de qualquer commit.
        await repo._db.rollback()  # type: ignore[attr-defined]
        raise ConflictError(
            "não foi possível salvar a classificação: outro imóvel já é a "
            "residência principal deste workspace",
            code="residencia_principal_conflict",
        ) from exc
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


async def _reject_second_residencia_principal(
    workspace_id: str,
    property_id: str,
    *,
    repo: PropertyRepository,
) -> None:
    """Recusa o 2º `residencia_principal` com mensagem acionável em vez de IntegrityError."""
    overrides = await repo.list_overrides(workspace_id)
    for pid, existing in overrides.items():
        if pid == property_id:
            continue
        if existing.classification != CLASSIFICATION_RESIDENCIA_PRINCIPAL:
            continue
        raise ConflictError(
            f"o imóvel {pid} já é a residência principal deste workspace; "
            "reclassifique-o antes de marcar outro",
            code="residencia_principal_conflict",
        )
