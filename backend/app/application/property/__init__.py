"""Use cases do agregado Property (ADR-215 P4)."""

from backend.app.application.property.list_properties import list_properties
from backend.app.application.property.set_property_classification import (
    set_property_classification,
)
from backend.app.application.property.set_residencia_status import set_residencia_status

__all__ = [
    "list_properties",
    "set_property_classification",
    "set_residencia_status",
]
