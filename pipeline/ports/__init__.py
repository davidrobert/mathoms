"""Ports — protocols read-only consumidos pelo pipeline (boundary stable, ADR-134)."""

from pipeline.ports.config_store import ConfigStore

__all__ = ["ConfigStore"]
