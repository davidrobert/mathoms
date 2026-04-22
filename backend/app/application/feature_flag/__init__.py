"""Use cases do agregado ``FeatureFlag`` (ADR-074 · ADR-101 R15)."""

from backend.app.application.feature_flag.get_feature_flags import (
    FlagsResponse,
    get_feature_flags,
)
from backend.app.application.feature_flag.set_feature_flag import (
    FlagUpdateCommand,
    set_feature_flag,
)

__all__ = [
    "FlagsResponse",
    "FlagUpdateCommand",
    "get_feature_flags",
    "set_feature_flag",
]
