"""Use cases do aggregate ``Protection`` (ADR-101 R15 · ADR-192)."""

from backend.app.application.protections.cancel_protection import cancel_protection
from backend.app.application.protections.create_protection import create_protection
from backend.app.application.protections.get_protection import get_protection
from backend.app.application.protections.link_to_risk import (
    link_to_risk,
    unlink_from_risk,
)
from backend.app.application.protections.list_protections import list_protections
from backend.app.application.protections.update_protection import update_protection

__all__ = [
    "cancel_protection",
    "create_protection",
    "get_protection",
    "link_to_risk",
    "list_protections",
    "unlink_from_risk",
    "update_protection",
]
