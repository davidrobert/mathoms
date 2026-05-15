"""Ports — protocols read-only consumidos pelo pipeline (boundary stable, ADR-134)."""

from pipeline.ports.config_store import ConfigStore
from pipeline.ports.property_identity_resolver import PropertyIdentityResolver

__all__ = ["ConfigStore", "PropertyIdentityResolver"]
