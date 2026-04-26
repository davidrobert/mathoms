"""Adapters concretos dos ports do pipeline (ADR-134)."""

from pipeline.adapters.file_config_store import FileConfigStore
from pipeline.adapters.in_memory_config_store import InMemoryConfigStore

__all__ = ["FileConfigStore", "InMemoryConfigStore"]
