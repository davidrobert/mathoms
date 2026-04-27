"""Pacote ``snapshot_changelog`` — builder determinístico de comparações (v2.D.1 · ADR-143)."""

from pipeline.domain.services.snapshot_changelog.builder import (
    DEFAULT_SECTION_LABELS,
    DEFAULT_SECTION_VALUE_PATHS,
    build_comparison,
    extract_section_value,
)
from pipeline.domain.services.snapshot_changelog.narratives import (
    format_summary,
)

__all__ = [
    "DEFAULT_SECTION_LABELS",
    "DEFAULT_SECTION_VALUE_PATHS",
    "build_comparison",
    "extract_section_value",
    "format_summary",
]
