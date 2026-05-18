"""Use cases do agregado Property (ADR-215 P4 + ADR-222)."""

from backend.app.application.property.list_properties import list_properties
from backend.app.application.property.set_imoveis_no_if import set_imoveis_no_if
from backend.app.application.property.set_property_classification import (
    set_property_classification,
)
from backend.app.application.property.set_residencia_status import set_residencia_status

__all__ = [
    "list_properties",
    "set_imoveis_no_if",
    "set_property_classification",
    "set_residencia_status",
]
