"""DTOs do agregado `Property` (ADR-215 P4)."""

from backend.app.schemas.dto.property.command import (
    PropertyClassificationCommand,
    ResidenciaStatusCommand,
)
from backend.app.schemas.dto.property.response import (
    PropertyListResponse,
    PropertyResponse,
    ResidenciaStatusResponse,
)

__all__ = [
    "PropertyClassificationCommand",
    "ResidenciaStatusCommand",
    "PropertyListResponse",
    "PropertyResponse",
    "ResidenciaStatusResponse",
]
