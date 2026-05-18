"""DTOs do agregado `Property` (ADR-215 P4)."""

from backend.app.schemas.dto.property.command import (
    ImoveisNoIfCommand,
    PropertyClassificationCommand,
    ResidenciaStatusCommand,
)
from backend.app.schemas.dto.property.response import (
    ImoveisNoIfResponse,
    PropertyListResponse,
    PropertyResponse,
    ResidenciaStatusResponse,
)

__all__ = [
    "ImoveisNoIfCommand",
    "ImoveisNoIfResponse",
    "PropertyClassificationCommand",
    "ResidenciaStatusCommand",
    "PropertyListResponse",
    "PropertyResponse",
    "ResidenciaStatusResponse",
]
