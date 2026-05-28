"""Definição da dataclass TypeRule — extraída para evitar ciclos de import (ADR-238 L4 split)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TypeRule:
    """A content-based document-type matcher."""

    code: str
    dest_group: str
    required: tuple[re.Pattern, ...]  # ALL must match
    supporting: tuple[re.Pattern, ...]  # at least one boosts confidence to 1.0
    priority: int = 100  # lower = evaluated first
    exclude: tuple[re.Pattern, ...] = ()  # ANY match vetoes the rule (negative guard)
