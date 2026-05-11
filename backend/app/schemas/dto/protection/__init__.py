"""DTOs do aggregate ``Protection`` (ADR-192)."""

from backend.app.schemas.dto.protection.bundle import (
    ProtectionBundleResponse,
    ProtectionGapItemResponse,
    ProtectionItemResponse,
    ProtectionRecommendationResponse,
    ProtectionThresholdsResponse,
    RiskInferredResponse,
)
from backend.app.schemas.dto.protection.command import (
    ProtectionCancelCommand,
    ProtectionCreateCommand,
    ProtectionLinkToRiskCommand,
    ProtectionUpdateCommand,
)
from backend.app.schemas.dto.protection.mapper import (
    brl_to_cents,
    cents_to_brl,
    protection_to_bundle_item,
    protection_to_response,
)
from backend.app.schemas.dto.protection.response import (
    ProtectionListResponse,
    ProtectionResponse,
)

__all__ = [
    "ProtectionBundleResponse",
    "ProtectionCancelCommand",
    "ProtectionCreateCommand",
    "ProtectionGapItemResponse",
    "ProtectionItemResponse",
    "ProtectionLinkToRiskCommand",
    "ProtectionListResponse",
    "ProtectionRecommendationResponse",
    "ProtectionResponse",
    "ProtectionThresholdsResponse",
    "ProtectionUpdateCommand",
    "RiskInferredResponse",
    "brl_to_cents",
    "cents_to_brl",
    "protection_to_bundle_item",
    "protection_to_response",
]
