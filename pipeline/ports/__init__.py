"""Ports — protocols read-only consumidos pelo pipeline (boundary stable, ADR-134)."""

from pipeline.ports.config_store import ConfigStore
from pipeline.ports.economic_assumptions_resolver import EconomicAssumptionsResolver
from pipeline.ports.property_identity_resolver import PropertyIdentityResolver
from pipeline.ports.property_overrides_resolver import PropertyOverridesResolver

__all__ = [
    "ConfigStore",
    "EconomicAssumptionsResolver",
    "PropertyIdentityResolver",
    "PropertyOverridesResolver",
]
