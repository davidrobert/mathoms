"""Kill-switch do mint sem canonical ([[ADR-392]]). Lido a cada chamada."""

from __future__ import annotations

import os

MINT_WITHOUT_CANONICAL_ENV = "MATHOMS_PROPERTY_MINT_WITHOUT_CANONICAL"


def mint_without_canonical_enabled() -> bool:
    return os.environ.get(MINT_WITHOUT_CANONICAL_ENV) == "1"
