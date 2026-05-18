"""Command DTOs do agregado Property (ADR-215 P4)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import (
    VALID_CLASSIFICATIONS,
    VALID_PROPERTY_OVERRIDE_SOURCES,
    VALID_RESIDENCIA_STATUSES,
)


class PropertyClassificationCommand(BaseModel):
    """`PUT /workspaces/{ws}/properties/{id}/classification`."""

    model_config = ConfigDict(extra="forbid")

    classification: str = Field(..., description="ADR-215 enum")
    override_source: str = Field(
        default="user_manual",
        description="user_manual | fuzzy_match_accepted | migration_keyword",
    )

    def validate_enums(self) -> None:
        """Valida classification + override_source contra enums (ADR-215)."""
        # Pydantic v2: a validação livre via field validator funciona, mas
        # mantemos checagem explícita para retornar 422 com mensagem clara.
        if self.classification not in VALID_CLASSIFICATIONS:
            raise ValueError(
                f"classification inválida: {self.classification!r}. "
                f"Esperado: {VALID_CLASSIFICATIONS}"
            )
        if self.override_source not in VALID_PROPERTY_OVERRIDE_SOURCES:
            raise ValueError(
                f"override_source inválido: {self.override_source!r}. "
                f"Esperado: {VALID_PROPERTY_OVERRIDE_SOURCES}"
            )


class ResidenciaStatusCommand(BaseModel):
    """`PUT /workspaces/{ws}/residencia-status`."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="owned | rented | undeclared")

    def validate_enums(self) -> None:
        if self.status not in VALID_RESIDENCIA_STATUSES:
            raise ValueError(
                f"status inválido: {self.status!r}. Esperado: {VALID_RESIDENCIA_STATUSES}"
            )


class ImoveisNoIfCommand(BaseModel):
    """`PUT /workspaces/{ws}/imoveis-no-if` (ADR-222)."""

    model_config = ConfigDict(extra="forbid")

    imoveis_no_if: bool = Field(
        ..., description="true: cat_2 entra em investivel_efetivo (ADR-142)."
    )
